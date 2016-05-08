# -*- coding: UTF-8 -*-
import pandas as pd
import requests
import gmplot
import json
import os.path
import numpy as np
import matplotlib.pyplot as plt

column_names = ['TransactionID', 'Price', 'Date', 'PostCode', 'PropertyType', 'Old/New', 'Duration', 'PAON', 'SAON', 'Street', 'Locality', 'City', 'District', 'County', 'PPD_Type', 'Record_Status']

sales13 = pd.read_csv('pp-2013.csv', header = None)
sales13.columns = column_names
sales13["Year"] = 2013
sales14 = pd.read_csv('pp-2014.csv', header = None)
sales14.columns = column_names
sales14["Year"] = 2014
sales15 = pd.read_csv('pp-2015.csv', header = None)
sales15.columns = column_names
sales15["Year"] = 2015
sales16 = pd.read_csv('pp-2016.csv', header = None)
sales16.columns = column_names
sales16["Year"] = 2016

sales = pd.concat([sales13, sales14, sales15, sales16], ignore_index=True)
#sales = pd.read_csv('pp-2015.csv', header = None)

#Select wether we want to search for more coordinates or not.
find_more_coords = True


print(sales.head())

#'Select only entries with PPD of type A, this is, standard private sales and with no NaN on PostCode
sales_clean = sales[sales['PPD_Type'] == 'A'].dropna(subset = ['PostCode'])


# We are going to focus on London, so:
sales_clean = sales_clean[sales_clean['City']=='LONDON']
print(sales_clean.head())

#Get unique London postcodes
postcodes = sales_clean['PostCode'].unique().tolist()

#Get postcodes that appear more than once
#postcodes = list(sales_clean['PostCode'].value_counts()[sales_clean['PostCode'].value_counts() >1].index.unique())

#Read postcode Locations from file if the file exists, otherwise access it through an API

#If the json file storing the postcode coordinates exist, let's just search only for new postcodes that may be persent on the data (e.g. if our database has been updated)
if os.path.isfile('postcode_coordinates.json'):
    with open('postcode_coordinates.json', 'r') as f:
        dict_coordinates = json.load(f)

        if find_more_coords:
            #Is there any missing postcodes on the dictionay?
            missing_postcodes = [i for i in postcodes if i not in dict_coordinates]
            #If there is actually some missing postcodes, let's search them on the API
            if len(missing_postcodes) > 0:
                #from lib import PostCodeClient
                #client = PostCodeClient()
                print('Calling API...')
                #missingpostcodesjson = [client.getLookupPostCode(i) for i in missing_postcodes]
                #Using a POST request would bemore efficient, however POST requests are limited to 100 postcodes and the API will stop responding if it gets many of them. For this reason, I found more convenient to make many GET calls and store the postcodes on a file, so that the API will only need to be called when data with new postcodes is added.
                missingpostcodesjson = [requests.get("https://api.postcodes.io/postcodes/" + i) for i in missing_postcodes]
                missing_postcodes_dict_list = [json.loads(i.content) for i in missingpostcodesjson]
                #Add the new postcodes to dict_coordinates
                for d in missing_postcodes_dict_list:
                    if u'result' in d:
                        dict_coordinates[str(d[u'result'][u'postcode'])] = (d[u'result'][u'latitude'], d[u'result'][u'longitude'])

#If the file does not exist, let's request all the postcode coordinates to the API and save them on a json file
else:
    #If file doesn't exist, search it on the API
    #Try to do it just using requests later on
    from lib import PostCodeClient
    client = PostCodeClient()
    print('Calling API...')
    allpostcodesjson = [client.getLookupPostCode(i) for i in postcodes]
    
    postcodes_dict_list = [json.loads(i) for i in allpostcodesjson]
    
    dict_coordinates = {}
    for d in postcodes_dict_list:
        if u'result' in d:
            dict_coordinates[str(d[u'result'][u'postcode'])] = (d[u'result'][u'latitude'], d[u'result'][u'longitude'])

#Store postcode_coordinates on a json file    
with open('postcode_coordinates.json', 'w') as f:
    json.dump(dict_coordinates, f)

#There were 4 postcodes for which our API failed to find, let's get rid of those rows
filter_postcode = [(sales_clean['PostCode'].loc[i] in dict_coordinates) for i in sales_clean['PostCode'].index]
sales_clean_postapi = sales_clean[filter_postcode]
#Let's add the location row
def get_location(row):
    return dict_coordinates[row['PostCode']]

sales_clean_postapi['Location'] = sales_clean_postapi.apply(get_location, axis = 1)

#Let's now make a heat map of allthe sales in London to see which are the most attractive areas in 2016
latitudes = [i[0] for i in sales_clean_postapi['Location']]
longitudes = [i[1] for i in sales_clean_postapi['Location']]

prices = np.array(sales_clean_postapi['Price'])

#Let's put just the Location and Price on a dataframe in order to be saved and uploaded into a webb up
df_Loc_Price = sales_clean_postapi[['Price']]
df_Loc_Price['Latitude']= latitudes
df_Loc_Price['Longitude'] = longitudes
df_Loc_Price.to_csv('LocationPrice.csv')

zoom = 14
rad = 30
gmap = gmplot.GoogleMapPlotter(51.5074, -0.1278, zoom)
gmap.heatmap(latitudes, longitudes, radius = rad)
gmap.draw("mymap.html")

#Cheap Map
mean_price = sales_clean_postapi["Price"].mean()
std_price = sales_clean_postapi["Price"].std()
sales_clean_postapi_cheap = sales_clean_postapi[sales_clean_postapi["Price"] <= mean_price - 0.2*std_price]
latitudes_cheap = [i[0] for i in sales_clean_postapi_cheap['Location']]
longitudes_cheap = [i[1] for i in sales_clean_postapi_cheap['Location']]

zoom = 14
rad = 30
gmap = gmplot.GoogleMapPlotter(51.5074, -0.1278, zoom)
gmap.heatmap(latitudes_cheap, longitudes_cheap, radius = rad)
gmap.draw("mymap_cheap.html")




#Range Map
low_price = 40000
high_price = 100000

sales_clean_postapi_range = sales_clean_postapi[(sales_clean_postapi["Price"] >= low_price) & (sales_clean_postapi["Price"] <= high_price) ]
latitudes_range = [i[0] for i in sales_clean_postapi_range['Location']]
longitudes_range = [i[1] for i in sales_clean_postapi_range['Location']]

zoom = 14
rad = 30
gmap = gmplot.GoogleMapPlotter(51.5074, -0.1278, zoom)
gmap.heatmap(latitudes_range, longitudes_range, radius = rad)
gmap.draw("map_range.html")


#Let's take a look at the average house price over time
average_price_over_time = sales_clean.groupby('Year')['Price'].mean()

#Fit a linear regresion model to predict the house cost in terms of location (Latitude and Longitude)
from sklearn.linear_model import LinearRegression
from sklearn import cross_validation
from sklearn.ensemble import RandomForestRegressor


predictors = [latitudes, longitudes]
targets = sales_clean_postapi['Price']
model = LinearRegression()

mean_score = (cross_validation.cross_val_score(model, np.array(predictors).T, targets, cv=10)).mean()

model.fit(np.array(predictors).T, targets)

latitudes_p = np.linspace(np.mean(latitudes)- np.std(latitudes),np.mean(latitudes)+ np.std(latitudes),100)
longitudes_p = np.linspace(np.mean(longitudes)- np.std(longitudes),np.mean(longitudes)+ np.std(longitudes),100)

latitudes_predict = []
longitudes_predict = []
for i in latitudes_p:
    for j in longitudes_p:
        latitudes_predict.append(i)
        longitudes_predict.append(j)


predictions = model.predict(np.array([longitudes_predict, latitudes_predict]).T)

import plotly.plotly as py
py.sign_in('edugp', 'aeddfi9lhd')
import plotly.graph_objs as go


z = []
for i in range(0,len(predictions),len(latitudes_p)):
    z.append(predictions[i: i+len(latitudes_p)])
zaxis = [go.Heatmap(z=z)]
plot_url = py.plot(zaxis, filename='Price_prediction_heatmap')
