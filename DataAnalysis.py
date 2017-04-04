import pandas as pd
import requests
import gmplot
import json
import os.path
import numpy as np
import matplotlib.pyplot as plt

#Read datasets
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

#Select wether we want to search for more postcode coordinates or not.
find_more_coords = True

#Select only entries with PPD of type A, this is, standard private sales and with no NaN on PostCode
sales_clean = sales[sales['PPD_Type'] == 'A'].dropna(subset = ['PostCode'])

# We are going to focus on London only, so:
sales_clean = sales_clean[sales_clean['City']=='LONDON']

#Get unique London postcodes
postcodes = sales_clean['PostCode'].unique().tolist()

#Read postcode locations from file if the file exists, otherwise access coordinates through an API
#If the json file storing the postcode coordinates exist, let's just search only for new postcodes that may be present on the data
if os.path.isfile('postcode_coordinates.json'):
    with open('postcode_coordinates.json', 'r') as f:
        dict_coordinates = json.load(f)
        if find_more_coords:
            #Is there any missing postcodes on the dictionay?
            missing_postcodes = [i for i in postcodes if i not in dict_coordinates]
            #If there is actually some missing postcodes, let's search them on the API
            if len(missing_postcodes) > 0:
                print('Calling API...')
                #Using a POST request would bemore efficient, however POST requests are limited to 100 postcodes.
                missingpostcodesjson = [requests.get("https://api.postcodes.io/postcodes/" + i) for i in missing_postcodes]
                missing_postcodes_dict_list = [json.loads(i.content) for i in missingpostcodesjson]
                #Add the new postcodes to dict_coordinates
                for d in missing_postcodes_dict_list:
                    if u'result' in d:
                        dict_coordinates[str(d[u'result'][u'postcode'])] = (d[u'result'][u'latitude'], d[u'result'][u'longitude'])

#If the file does not exist, let's request all the postcode coordinates to the API and save them on a json file
else:
    #If file doesn't exist, search using the API
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

#Get rid of those rows with postcodes not found
filter_postcode = [(sales_clean['PostCode'].loc[i] in dict_coordinates) for i in sales_clean['PostCode'].index]
sales_clean_postapi = sales_clean[filter_postcode]
#Let's add the location row
def get_location(row):
    return dict_coordinates[row['PostCode']]

sales_clean_postapi['Location'] = sales_clean_postapi.apply(get_location, axis = 1)

#Let's now make a heat map of all the sales in London to see which are the most attractive areas in 2016
latitudes = [i[0] for i in sales_clean_postapi['Location']]
longitudes = [i[1] for i in sales_clean_postapi['Location']]

prices = np.array(sales_clean_postapi['Price'])

#Create dataframe to be used by the web app
df_Loc_Price = sales_clean_postapi[['Price']]
df_Loc_Price['Latitude']= latitudes
df_Loc_Price['Longitude'] = longitudes
df_Loc_Price.to_csv('LocationPrice.csv')
