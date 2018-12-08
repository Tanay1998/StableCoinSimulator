from random import randint
from numpy.random import normal

from .constants import *
from .utils import *
from .market import Market
from .protocols import BasisProtocol

class Trader: 
    def __init__(self, tid, protocol, market):
        self.tid = tid
        self.protocol = protocol
        self.market = market
        self.portfolioRatio = 0.5
        self.eth = 10
        self.bas = 1000
        self.bondsLiquidated = 0
        
    def liquidate(self, amount):
        self.bas += amount
        self.bondsLiquidated += amount
        
    def get_price(self, side, base_price):        
        # Set price around BASE_PRICE
        price = normal(base_price, PRICE_NOISE)
        if side == 'bid':
            price -= (base_price * BASE_SPREAD) 
        else:
            price += (base_price * BASE_SPREAD) 
        return clamp_bas_price(price)
        
    def get_qty(self):
        qty_mu = self.portfolioRatio
        qty_sigma = qty_mu * 0.1
        qty = normal(qty_mu, qty_sigma) * self.bas
        return clamp_bas_qty(qty)
        
    def getIdealValue(self):
        return self.eth * 100 + self.bas

    def marketStep(self):
        return None
    
'''
    IdealTrader buys/sells according to market demand. 
    Sets prices to be around the ideal exchange rate ~ 0.01.
'''
class IdealTrader(Trader):
    def __init__(self, tid, protocol, market):
        super().__init__(tid, protocol, market)
        self.bas = int(1e5) # $100,000 in BASIS 
        self.portfolioRatio = 0.05
        
    def marketStep(self):
        # Randomly select bid / ask based on market demand
        side = ['bid', 'ask'][biased_coin(0.5)]
        
        # Set Quantity around portfolio ratio 
        qty = self.get_qty()

        if qty <= 0:
            return None
        
        # Set price around BASE_PRICE
        price = self.get_price(side, self.market.usd_eth)
        
        order = {'type': 'limit', 'price': price, 'tid': self.tid, 'side': side, 'qty': qty}
        return order
    
class RandomTrader(Trader): 
    def __init__(self, tid, protocol, market):
        super().__init__(tid, protocol, market)
        self.portfolioRatio = 0.05
        self.bas = int(1e4)
        
    def marketStep(self):
        # Set Quantity around portfolio ratio 
        qty = self.get_qty()
        
        if qty <= 0:
            return None
        
        # Randomly select bid / ask based on market demand
        side = ['ask', 'bid'][biased_coin(self.market.demandRatio)]
        
        # Try to see if need for BAS can be satisfied with liquidated bonds
        if side == 'bid' and self.bondsLiquidated:
            if self.bondsLiquidated > qty:
                self.bondsLiquidated -= qty
                return None
            else:
                qty -= self.bondsLiquidated
                self.bondsLiquidated = 0
        
        # If there is high confidence, then buy bonds in the auction.
        if side == 'ask' and biased_coin(self.market.demandRatio) and self.protocol.bondsForAuction:
            # Buy the bonds for a price 
            price = randint(90, 99) * 0.01 # Gets the price the person is willing to pay for the bonds
            qty = min(qty, self.protocol.bondsForAuction)
            qty = min(qty, self.bas / price)
            self.protocol.issueBonds(self.tid, qty)
            burntBasis = price * qty
            self.bas -= burntBasis
            self.protocol.totalSupply -= burntBasis
            return None
        
        # Set price around BASE_PRICE
        price = self.get_price(side, self.market.getIdealETHValue())
        
        order = {'type': 'limit', 'price': price, 'tid': self.tid, 'side': side, 'qty': qty}
        return order

    
class InvestorTrader(Trader): 
    def __init__(self, tid, protocol, market):
        super().__init__(tid, protocol, market)
        self.portfolioRatio = 0.001
        self.bas = int(1e7)
        self.eth = 1000
    
class TrendMaker(Trader):
    pass

class BasicTrader(Trader): 
    def __init__(self, tid, protocol, market):
        super().__init__(tid, protocol, market)
        self.portfolioRatio = 0.05
        self.threshold = BASIC_TRADER_THRESHOLD
        self.bas = int(1e4)
        
    def marketStep(self):
        # Set Quantity around portfolio ratio 
        qty = self.get_qty()
        
        if qty <= 0:
            return None
        
        # Randomly select bid / ask based on market demand
        if self.market.getCurrentUSDValue() <= 1.0 - self.threshold:
            side = 'bid'
        elif self.market.getCurrentUSDValue() >= 1.0 + self.threshold:
            side = 'ask'
        else:
            return None
        
        if self.market.demandRatio < 0.2 and side == 'bid':
            return None
        
        if self.market.demandRatio > 0.8 and side == 'ask':
            return None
        
        # Set price around BASE_PRICE
        price = self.get_price(side, self.market.getIdealETHValue())
        
        order = {'type': 'limit', 'price': price, 'tid': self.tid, 'side': side, 'qty': qty}
        return order

trader_dict = {'IdealTrader': IdealTrader, 'RandomTrader': RandomTrader, 'TrendMaker': TrendMaker, 
               'BasicTrader': BasicTrader, 'InvestorTrader': InvestorTrader}


# Implement TrendMaker, ShareTokens, ShareHolderTrader
def createTraderPool(protocol, market, demographics):
    traderPool = {}
    uniqTID = 1
    for trader_type, number in demographics.items():
        trader_class = trader_dict[trader_type]
        for i in range(number):
            trader = trader_class(uniqTID, protocol, market)
            traderPool[uniqTID] = trader
            uniqTID += 1
    return traderPool