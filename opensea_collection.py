#!/usr/bin/env python3
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import powerlaw
import math

collectionCSVs = [
    "0n1_force.csv",
    "axie_infinity.csv",
    "azuki.csv",
    "bored_ape.csv",
    "clone_x.csv",
    "coolmonkes.csv",
    "creature_world.csv",
    "creepz_reptile.csv",
    "creeps.csv",
    "cryptoadz.csv",
    "cryptobatz.csv",
    "cryptokitties.csv",
    "cryptopunks.csv",
    "cryptoskulls.csv",
    "cyberkongz_vx.csv",
    "DeadFellaz.csv",
    "decentraland_wearables.csv",
    "doge_pound.csv",
    "doodles.csv",
    "dr_ETHvil.csv",
    "emblem_vaul.csv",
    "FLUF_world_thingies.csv",
    "fomo_mofos.csv",
    "full_send.csv",
    "hape_prime.csv",
    "hashmasks.csv",
    "lil_heroes.csv",
    "lostpoets.csv",
    "meebits.csv",
    "mekaverse.csv",
    "metroverse.csv",
    "mutant_ape.csv",
    "my_curio_cards.csv",
    "phantabear.csv",
    "pudgypenguins.csv",
    "punkcomics.csv",
    "rarible.csv",
    "rtfkt.csv",
    "sorare.csv",
    "superrare.csv",
    "wolf_game.csv",
    "world of women.csv",
    "wvrps.csv",
    "x_rabbits.csv"
]

class collection():
    """The collection class is meant to act as a holder, the idea is that for each of the CSVs above, we can
    load them in by name, all of the necessary calculations can be done on initialization, and later
    on when we want some useful visualizations of the data at the end we can call the proper methods.
    
    Params
    ------
    name - The name of the collection from the above list of csvs.
    
    Methods
    -------
    """
    def __init__(self, name):
        self.name = name
        self.cwd = os.getcwd()
        directory = self.cwd + '/data/' + self.name
        self.panda = pd.read_csv(directory, low_memory=False)
        #Now we do the work on it
        self.panda = self.clean_panda(self.panda)
        #print(f'Keys: {panda.keys()}')
        self.panda['adj_price'] = self.make_adjprice(self.panda)
        #print(f'Keys: {panda.keys()}')
        self.roundness = self.roundness_check(self.panda['adj_price'])
        self.panda['eth_first_sig'] = self.make_first_sig(self.panda['adj_price'])
        single, tenths, hundreths = self.make_eth_clusters(self.panda['adj_price'])
        self.panda['eth_single'] = single
        self.panda['eth_tenths'] = tenths
        self.panda['eth_hundreths'] = hundreths
        self.panda['usd_price'] = self.make_usdprice(self.panda['adj_price'], self.panda['payment_token_usd_price'])
        self._make_usd_first_sig(self.panda['usd_price'])
        self._make_fusd()
        
    def clean_panda(self, dataframe):
        """
        Takes in a Panda dataframe read from an opensea csv, drops bad rows, 
        bundle data, non ETH transactions then deletes original panda from memory.

        Params
        ------
        panda - The panda to take in

        Returns
        -------
        cleaned_dataframe - The cleaned dataframe
        """
        def main(dataframe):
            dataframe = drop_bad_rows(dataframe)
            dataframe = drop_bundle(dataframe)
            dataframe = drop_nETH(dataframe)
            dataframe.reset_index(inplace=True, drop=True)
            return dataframe
        
        def drop_bad_rows(dataframe):
            ret = dataframe.dropna(subset=['total_price'])
            return ret
        
        def drop_bundle(dataframe):
            return dataframe.iloc[:, 1:150]
        
        def drop_nETH(dataframe):
            # What happens if there are no non ETH indices? 
            # Likely needs error handling
            bad_indices = dataframe[(dataframe.payment_token_id != 1) & (dataframe.payment_token_id != 2)].index
            ret = dataframe.drop(bad_indices)
            return ret
        
        return main(dataframe)
            
    def make_adjprice(self, dataframe):
        #Make an adj_price column to represent ETH price
        adj_price = dataframe.apply(lambda row: float(row.total_price) / (10**row.payment_token_decimals), axis = 1)
        return adj_price
    
    def roundness_check(self, adj_prices):
        def last_sig_fig(number):
            """
            Returns an integer indicating how many places after the decimal the last significant digit is. 1 returned is considered to be 
            the tenths place, while -1 would indicate the ones place
            
            Params
            ------
            number - the number to find the last sigfig of
            
            Returns
            -------
            The integer representation of the last sigfig's place
            """
            
            if type(number) != float and type(number) != int:
                raise ValueError(f'{number} is neither a float or int')
            
            #Convert to string to use indexing
            strnum = str(number)
            
            def calc_ones(strnum):
                last_sig_index = -9999
                #Strip decimal if we have one
                if '.' in strnum:
                    strnum = strnum[0:strnum.rfind('.')]
                #Get length -1 for range
                length = len(strnum)
                for i in range(0, length):
                    if strnum[i] != '0':
                        last_sig_index = i
                if last_sig_index != -9999:
                    return -(len(strnum) - last_sig_index)
                else:
                    #Edge case where we're processing 0.0
                    return -1
                
            #0 and 1 can both be confused in boolean expressions, uses a decided 'null' value instead.
            last_sig_index = -9999
            if '.' in strnum:
                #rfinds gets the index of last .
                dec_loc = strnum.rfind('.')
                for i in range(dec_loc+1, (len(strnum))):
                    #Zeros after the . will never be the last sigfig
                    if strnum[i]!='0':
                        last_sig_index = i
                #We found sigfig past decimal
                if last_sig_index != -9999:
                    #Return the last occurence, but first calculate the place:
                    return last_sig_index-dec_loc
            #If there isnt a decimal, or we didn't find a sigfig past
            return calc_ones(strnum)
        
        counts = np.empty(0)
        for adj_price in adj_prices:
            #Find the last significant digit
            place = last_sig_fig(adj_price)
            counts = np.append(counts, place)
            """if (place < -4) | (place > 5) | (place == 0):
                raise Exception(f'Sigfig was: {place} and adj_price = {adj_price}' +
                                '. Considered outside of the realized bounds, and therefore has not been accounted for')"""
            """#Then increment the list
            if place == -4:
                thousands = thousands+1
            elif place == -3:
                hundreds = hundreds+1
            elif place == -2:
                tens = tens + 1
            elif place == -1:
                ones = ones + 1
            elif place == 1:
                tenths = tenths + 1
            elif place == 2:
                hundreths = hundreths + 1
            elif place == 3:
                thousandths = thousandths + 1
            elif place == 4:
                ten_thousandths = ten_thousandths + 1
            elif place == 5:
                hundred_thousandths = hundred_thousandths + 1
                
        return {'hundred_thousandths':hundred_thousandths, 'ten_thousandths':ten_thousandths, 'hundreths': hundreths, 'tenths': tenths, 
            'ones':ones, 'tens':tens, 'hundreds':hundreds, 'thousands':thousands}"""
        number, occurrences = np.unique(counts, return_counts=True)
        returndict = {}
        j = 0
        for i in number:
            returndict[f'{i}']=occurrences[j]
            j = j + 1
        return returndict
    
    def make_first_sig(self, adj_price):
        def first_sig_fig(number):
            """
            Returns the first significant digit of a provided number as string
            
            Parameters
            ----------
            number: The number whose first significant digit will be returned
            
            Raises
            ------
            TypeError: If the provided variable is not a number a TypeError will be raised
            """
            #Check that what is provided is actually a number
            if type(number) != int and type(number) != float and isinstance(number, np.ndarray) == False:
                raise TypeError(f"{number} is not a number, it is of type {type(number)}")
            
            #Turn number into string so that it's iterable
            snumber = str(number)
            
            #Sentinel value to determine if we've hit the decimals yet.
            decimal_encountered = False
            for i in range(0,len(snumber)):
                if snumber[i].isdigit():
                    temp = snumber[i]
                    if snumber[i] == '0':
                        pass
                    else:
                        return snumber[i]
                else:
                    pass
        
        #Build the series to return with the function
        series = []
        for i in adj_price:
            series.append(first_sig_fig(i))
        return series
    
    def make_eth_clusters(self, adj_price):
        """
        Takes in the adj price representing the total ETH/WETH traded, which is
        stored in the panda from opensea csv, returns two columns to be added by using the float round function.
        
        Params
        ------
        adj_price - The adj price series in a panda representing the ETH/WETH amounts
        
        Returns
        -------
        As a tuple ('single_digit, tenths, hundreths')
        single_digit - A series containing the ETH/WETH as a integer
        tenths - A series containing the ETH/WETH as a float and one decimal place
        hundreths - A series containing the ETH/WETH as float and two decimal places
        """
        
        #Single round
        single_digit = []
        for i in adj_price:
            single_digit.append(round(i))
        
        #Tenths
        tenths = []
        for i in adj_price:
            tenths.append(round(i, 1))
        
        #Hundreths
        hundreths = []
        for i in adj_price:
            hundreths.append(round(i, 2))
        
        return single_digit, tenths, hundreths
    
    def make_usdprice(self, adj_price, payment_token_eth_price):
        """
        Generates the USD price for the panda using pythons built in zip class
        
        Params
        ------
        
        Returns
        -------
        """
        series = []
        for i, j in zip(adj_price, payment_token_eth_price):
            series.append(i*j)
        return series

    def plot_eth_fsd(self):
        """
        Plots the benford standard in ETH/WETH
        I think its important that this function is also recreated using
        USD. While benford distribution might not be followed with coin amount,
        benford distribution may be closer in USD.
        
        Params
        ------
        
        Returns
        -------
        """
        
        values = self.panda['eth_first_sig'].value_counts().sort_index()
        percentages = []
        
        for i in values:
            #Get the percentage rather than the count
            percentages.append((i/sum(values))*100)
        
        x = [1, 2, 3, 4, 5, 6, 7, 8, 9]
        plt.style.use('seaborn')
        plt.bar(x,percentages, width=0.75)
        plt.xticks(x)
        
        #This handles overlaying the benford standard dots
        benford_standard = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
        plt.scatter(x, benford_standard, c='black')
        plt.xlabel('First Significant Digit')
        plt.ylabel('Percentage')
        
        #Probably want to change this for the report
        plt.title(self.name)
        plt.show()

    def plot_usd_fsd(self):
        """
        Plots the beford standard in USD.
        
        Params
        ------
        
        Returns
        -------
        """
        values = self.panda['usd_first_sig'].value_counts().sort_index()
        percentages = []
        for i in values:
            #Get the percentage rather than the count
            percentages.append((i/sum(values))*100)
        
        #Plot the actual percentages and set appropriate ticks
        plt.style.use('seaborn')
        x = [1, 2, 3 , 4, 5, 6, 7, 8, 9]
        plt.bar(x,percentages, width=0.75)
        plt.xticks(x)
        
        #This handles overlaying the benford standard dots
        benford_standard = [30.1, 17.6, 12.5, 9.7, 7.9, 6.7, 5.8, 5.1, 4.6]
        plt.scatter(x, benford_standard, c='black')
        plt.xlabel('First Significant Digit')
        plt.ylabel('Percentage')
        
        #Probably want to change this for the report
        plt.title(self.name)
        
        plt.show()
        
    def _make_usd_first_sig(self, usd_price):
        def first_sig_fig(number):
            """Returns the first significant digit of a provided number as string
            
            Parameters
            ----------
            number: The number whose first significant digit will be returned
            
            Raises
            ------
            TypeError: If the provided variable is not a number a TypeError will be raised
            """
            #Check that what is provided is actually a number
            if type(number) != int and type(number) != float and isinstance(number, np.ndarray) == False:
                raise TypeError(f"{number} is not a number, it is of type {type(number)}")
            #Turn number into string so that it's iterable
            snumber = str(number)
            #Sentinel value to determine if we've hit the decimals yet.
            decimal_encountered = False
            for i in range(0,len(snumber)):
                if snumber[i].isdigit():
                    temp = snumber[i]
                    if snumber[i] == '0':
                        pass
                    else:
                        return snumber[i]
                else:
                    pass
        series = []
        for i in usd_price:
            series.append(first_sig_fig(i))
        self.panda['usd_first_sig'] = series
    
    def _make_fusd(self):
        """
        Makes a floating point usd column for the panda.
        
        This is the way I should have structured each function
        that was supposed to update the panda, instead of setting
        the value in the initialization of the object, haven't
        changed over all the methods due to time constraints.
        """
        #Would usually return a generator object, by calling list python forces
        #the list comprehension to be saved to memory
        self.panda['fusd_price'] = list(float(usd) for usd in self.panda['usd_price'])
        
    def plot_usd_tail(self):
        """ 
        This method consists of plotting the logarithm of an estimator
        of the probability that a particular number of the distribution occurs 
        versus the logarithm of that particular number. 
        Usually, this estimator is the proportion of times that the number occurs in the data set
        We want to generate the top 10 percent of the data set (aka the tail end of the distribution) 
        
        Params
        ------
        
        Returns
        -------
        """
        length = len(self.panda['adj_price'])
        #Get the top ten percent of trades
        ten_percent = math.floor(length/10)
        top_ten_istart = length-ten_percent
        top_ten_counts = self.panda['adj_price'][top_ten_istart:].value_counts().sort_index()
        
        #Calling the powerlaw function attempts to fit the data in top ten counts
        results = powerlaw.Fit(top_ten_counts)
        
        #Optional print statements to determine tail exponent
        #print(f'alpha: {results.power_law.alpha}')
        #print(f'xmin: {results.power_law.xmin}')
        
        #Calling this function evaluates how close the data's distribution was to a powerlaw distribution, 
        #Compared to a lognormal distribution, I was getting very low coefficients for powerlaw distributions
        R, p = results.distribution_compare('power_law', 'lognormal')
        print(f'R: {R} , p: {p}')
        
        #This will plot the value counts on a log log plot
        #Powerlaw distributions usually conform into a straight line,
        #but the scatter plots I was testing with did not, possibly not enough data
        #collection to collection to get a good distribution.
        """fig = plt.figure(figsize=(5, 6))
        ax1 = fig.add_subplot()
        plt.loglog()
        plt.scatter(top_ten_counts.index, top_ten_counts, c='r')
        plt.show()"""
        
        #ax2 = fig.add_subplot()
        #fit = powerlaw.Fit(top_ten_counts)
        #x,y = powerlaw.pdf(top_ten_counts, linear_bins=False)
        #print(f'{len(top_ten_counts)} counts, and x: {x} and y:{y}')
        #ind = y>0
        #y = y[ind]
        #x = x[:-1]
        #x = x[ind]
        #ax1.scatter(x, y, color='r', s=.5)
        ##linear_model=np.polyfit(x,y,1)
        ##linear_model_fn=np.poly1d(linear_model)
        #ax1.plot(x, linear_model_fn)
        #powerlaw.plot_pdf(top_ten_counts[top_ten_counts>0], ax=ax1, color='b', linewidth=2)
        #powerlaw.plot_pdf(sorted(top_ten_counts, reverse=True), ax=ax1, color='b', linewidth=2)
        #plt.show()
        
        # Heres where I was a little confused, calculating the probability 
        # density also can be done by using the probability density function
        # (PDF). This function is calculated by making a histogram of value counts (frequencies),
        # and then the value at any point is calculated by taking the area 
        # underneath a curve that fits the heights of the histogram
        # this is the probability density (PD) which was plotted against trade size
        # in Dr. Li's paper on crypto wash trading.
        # create log bins: (by specifying the multiplier)
        
        """
        What this function was supposed to do can be seen at the following link
        http://www.mkivela.com/binning_tutorial.html
        
        bins = [np.min(self.panda['fusd_price'])]
        cur_value = bins[0]
        multiplier = 2.5
        while cur_value < np.max(values):
            cur_value = cur_value * multiplier
            bins.append(cur_value)
        
        bins = np.array(bins)
        pdf, bins, _ = ax2.hist(values, bins=len(values), density=True)"""
        
        """_ = ax2.scatter(x=top_ten, y=pdv, norm=True)
        ax2.set_title('PDF, log-log, power-law')
        ax2.set_xscale('log')
        ax2.set_yscale('log')
        ax2.set_xlabel('x')
        ax2.set_ylabel('PDF')
        plt.show()"""
    
    def plot_cluster(self, prange):
        """"
        Plots and displays a histogram from 0 to prange,
        also highlights every 5th bin to accentuate clustering.
        
        Params
        ------
        prange - the max range to display as an integer or float
        
        Raises
        ------
        TypeError - if the range provided is not an int or float.
        """
        if not isinstance(prange,int) and not isinstance(prange, float):
            raise TypeError('Range provided must be an int or a float')
        if (prange > max(self.panda.eth_hundreths)):
            raise ValueError(f'The range provided {prange} was greater' +
                             f'than the max transaction size {max(self.panda.eth_hundreths)}')
        #Make the figure
        fig = plt.figure(figsize=(8,6))
        plt.style.use('seaborn')
        ax1 = fig.add_subplot()
        
        category = 'eth_'
        if prange < 10:
            category = category + 'hundreths'
            true_range = prange + 0.01
        elif prange < 100:
            category = category + 'tenths'
            true_range = prange + 0.1
        else:
            category = category + 'singles'
            true_range = prange + 1
        
        #Make the histogram for the figure
        n, bins, patches = ax1.hist(self.panda[category], align='mid', bins=101, range=(0,true_range), color='gray')
        
        counter = 0
        print(f'Patches: {patches}')
        for i in range(0, len(patches)):
            if counter % 5 == 0:
                patches[i].set_fc('k')
            counter = counter + 1
        plt.show()
        
    def t_test(self):
        """
        Creates a histogram to bin values within the observation window, 
        builds the cluster point frequency and highest frequency of a neighbor 
        within the bounds into a tuple. The tuple is appended to a list and the
        proccess is repeated untill we have the final list of all observations.
        The student t-test is then performed at 1, 5, and 10% levels of 
        significance.
        
        Currently working on this. Also trying to determine if using 
        different units then presented in the paper by Dr. Li will
        give us a better statistical analysis
        
        Params
        ------
        
        Returns
        -------
        """
        #print(max(self.panda['adj_price']))
        max_eth_traded = max(self.panda['adj_price'])
        if (max_eth_traded) > 100:
            max_eth_traded = 100
        its_tenths = int(max_eth_traded*10)
        #Each iteration should be 100+50 and then repeat 0.01 is the unit 
        #Each iteration should be 500+100  0.05 is the unit.
        #Each iteration should be at 1000+500 0.1 is the unit
        #Each iteration should be at 5000+10 0.5 is the unit.
        fig = plt.figure(figsize=(5,6))
        ax1 = fig.add_subplot()
        
        lowerbound = 0.05
        upperbound = 0.15
        all_observations=[]
        for i in range(0, its_tenths):
            counts, bins, rects = ax1.hist(self.panda['eth_hundreths'], bins=10, range=(lowerbound, upperbound), align='mid')
            #Calculate the percentage of the cluster
            all_counts = sum(counts)
            cluster_freq = round((counts[5]/all_counts*100), 2)
            #Calculate the highest 
            counts[5] = 0.0
            #For testing purposes, also store a third number which will tell us
            #Which number range is housing more than a cluster
            ind_hn = counts.argmax()
            offender = lowerbound + ind_hn
            offender = round(offender, 2)
            highest_neighbor = round((max(counts)/all_counts*100), 2)
            #Build a tuple and add it to all views
            this_observation = (cluster_freq, highest_neighbor, offender)
            all_observations.append(this_observation)
            #Increment the lower and upper
            lowerbound = lowerbound + .10
            upperbound = upperbound + .10
            #Repeat
        self.observations = all_observations
        
        
        
        #ax1.xaxis.set_major_formatter(FormatStrFormatter('%0.2f'))
        #ax1.set_xticks(bins)
        #plt.show()
if __name__ == '__main__':
    """
    Heres where I've been testing all the functions that I'm creating
    just create an object from a csv that you have in your data folder,
    init methods will be run on instantiation which handle getting the
    panda prepared, and then you can call any of the functions above.
    """
    test = collection(collectionCSVs[22])
    test.t_test()
    # nan results likely due to no transactions falling within a region
    # multiplying 0 in numpy probably returns nan
    #print(test.observations)