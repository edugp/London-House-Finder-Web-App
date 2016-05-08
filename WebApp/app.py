from flask import Flask, render_template, request, redirect
import pandas as pd
import gmplot
import requests
import json
from bokeh.io import output_file, show, save
from bokeh.models import (
  GMapPlot, GMapOptions, ColumnDataSource, Circle, DataRange1d, PanTool, WheelZoomTool, BoxSelectTool, HoverTool
)


app = Flask(__name__)

app.ticker = ''
app.state = 'input'
app.option = 'Heatmap'

@app.route('/')
def main():
	if app.state == 'input':
		return redirect('/index')
	else:
		return redirect('/result')


@app.route('/index', methods=['GET'])
def index():
	return render_template('index.html')

@app.route('/index', methods=['POST'])
def index2():
	app.minprice = request.form['minprice']
	app.maxprice = request.form['maxprice']
	app.option = request.form['option']
	app.postcode = request.form['postcode']
	app.radius = request.form['radius']
	app.property_type = request.form['property_type']

	print('post')

	app.state = 'output'
	return redirect('/')

@app.route('/result', methods=['GET'])
def plot_result():
	app.state = 'input'

	#Extract relevant data
	if app.option == 'Heatmap' or app.option == 'Zoopla':

		print('Loading Zooplas data...')


		#Extract house listings from Zoopla
		radius = app.radius
		if not radius:
			radius = 0
		postcode = app.postcode
		area = 'London'
		if not app.minprice:
			app.minprice = '0'
		min_price = app.minprice
		if not app.maxprice:
			app.maxprice = '100000000'
		max_price = app.maxprice
		listing_status = app.property_type

		property_listings_api = 'http://api.zoopla.co.uk/api/v1/property_listings.json?'
		if len(postcode.split()) < 2:
			postcode_api = '&postcode=' + postcode
		else:
			postcode_api = '&postcode=' + postcode.split(' ')[0] + postcode.split(' ')[1]
		radius_api = '&radius=' + str(radius)
		area_api = '&area=' + area
		page_size = 100
		order_by = 'age'
		min_price_api = '&minimum_price=' + str(min_price)
		max_price_api = '&maximum_price=' + str(max_price)
		listing_status_api = '&listing_status=' + listing_status
		page_size_api = '&page_size=' + str(page_size)
		order_by_api = '&order_by=' + order_by
		api_key = '&api_key=' + 'wj9824uaekvke3ap8tq3cr8t'

		if not postcode:
			response = requests.get(property_listings_api + area_api + listing_status_api + min_price_api + max_price_api + page_size_api + order_by_api +api_key).json()
		else:
			response = requests.get(property_listings_api + postcode_api + radius_api + listing_status_api + min_price_api + max_price_api + page_size_api + order_by_api +api_key).json()
		listing_lats = [i['latitude'] for i in response['listing']]
		listing_longs = [i['longitude'] for i in response['listing']]
		listing_urls = [i['details_url'] for i in response['listing']]
		listing_phones = [i['agent_phone'] for i in response['listing']]
		listing_agents = [i['agent_name'] for i in response['listing']]
		listing_ids = [i['listing_id'] for i in response['listing']]
		listing_addresses = [i['displayable_address'] for i in response['listing']]
		listing_prices = [i['price'] for i in response['listing']]

		if app.option == 'Heatmap':

			app.df=pd.read_csv('LocationPrice.csv')
			app.filter = ((app.df["Price"].astype('int') >= int(app.minprice)) & (app.df["Price"].astype('int') <= (int(app.maxprice)))).tolist()
			app.df = app.df[app.filter]

			#Draw plot
			zoom = 12
			rad = 40
			gmap = gmplot.GoogleMapPlotter(51.5074, -0.1278, zoom)
			if app.property_type =='sale':
				gmap.heatmap(app.df['Latitude'].tolist(), app.df['Longitude'].tolist(), radius = rad)

			#gmap.plot(listing_lats, listing_longs, 'cornflowerblue', edge_width=10)
			gmap.scatter(listing_lats, listing_longs, '#3B0B39', size=50, marker=False)

			gmap.draw("templates/map.html")
		else:
			map_options = GMapOptions(lat=51.528308, lng=-0.1278, map_type="roadmap", zoom=11)
			plot = GMapPlot(
			    x_range=DataRange1d(), y_range=DataRange1d(), map_options=map_options, title="London", plot_width=1325, plot_height=615, #toolbar_location="below"
			)

			source = ColumnDataSource(
			    data=dict(
			        lat=listing_lats,
			        lon=listing_longs,
			        url=listing_urls,
			        price=listing_prices,
			        phone=listing_phones,
			        name=listing_agents,
			        address=listing_addresses,
			        id=listing_ids,
			    )
			)
			hover = HoverTool(
		       tooltips=[
		      ("Zoopla Listing ID", "@id"),
		      ("Address", "@address"),
		      ("Price", "@price"),
		      ("Agent", "@name"),
		      ("Phone", "@phone"),
		    ]
			)
			circle = Circle(x="lon", y="lat", size=12, fill_color="red", fill_alpha=0.8, line_color=None)
			plot.add_glyph(source, circle)
			plot.add_tools(PanTool(), WheelZoomTool(), hover)

			output_file("templates/map.html")
			save(plot)

		return render_template('map.html')

	return render_template('choropleth.html')
if __name__ == '__main__':
	app.run(port=33507)

