# London-House-Finder-Web-App

#Check WebApp live at: http://londonhouseprices.herokuapp.com

DataAnalysis.py is the script used to clean and analyze the UK Government's price paid dataset from https://www.gov.uk/government/statistical-data-sets/price-paid-data-downloads from 2014 to 2016 and obtain the coordinates of each postcode present on the dataset through postcodes.io API, storing the resulting dataframe containing property transaction price and coordinates.

WebApp folder contains the web app built on Flask and deployed in Heroku (http://londonhouseprices.herokuapp.com) to visualize a Heatmap of the probability of finding a house within a specific price range as well as an interactive map containing information from Zoopla listings within a specific price range and location.

CreateChoroplethMap.py contains the code to generate the choropleth map for the average property prices of London's neighbourhoods.
