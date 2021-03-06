import catsHTM
import pandas as pd
import sys
from astropy.coordinates import Angle
from astropy import units as u
from astropy.coordinates import SkyCoord as skycoord
from math import *
import urllib
import requests	
import numpy as np

par = {"catsHTM_rootpath":"/mnt4/data/ewittmyl/catalogs/"}

def simbad_check(ra, dec, srad):

	# We use the Simbad script-interface to make our queries.

	# Simbad script-interface URL:
	url = "http://simbad.u-strasbg.fr/simbad/sim-script?script="

	# Our search-script. This can be modified to produce different outputs.
	# Current version will produce each entry in the format:
	# offset (arcsec) | identifier | objtype | RA (deg) | Dec (deg) | U mag | B mag | V mag | R mag | I mag
	script = "output console=off script=off\nformat object form1 \"%DIST | %IDLIST(1) | %OTYPE(S) | %COO(:;A;d) " \
			 "| %COO(:;D;d) | %FLUXLIST(U)[%6.2*(F)] | %FLUXLIST(B)[%6.2*(F)] | %FLUXLIST(V)[%6.2*(F)] " \
			 "| %FLUXLIST(R)[%6.2*(F)] | %FLUXLIST(I)[%6.2*(F)]\"\nquery coo "+str(ra)+" "+str(dec)+" "\
			 +"radius="+str(srad)+"s frame=ICRS"

	# Encode the script as URL and build the full search URL-string:
	enc_script = urllib.parse.quote(script)
	search_url = str(url)+str(enc_script)

	# Produce the output-tables (we know what the columns and their units should be; out-table starts
	# empty and we fill it only if sensible results were obtained.
	colcell = ["offset", "identifier", "otype", "ra", "dec", "umag", "bmag", "vmag", "rmag", "imag" ]
	colunits = ["arcsec", "", "", "deg", "deg", "", "", "", "", ""]
	out_table = []

	# Try the search. If it fails, return an empty list and a flag indicating FAILURE, otherwise assume we got a valid table.
	try:
		contents = requests.get(search_url).text	# The actual http-request command for the URL described above
	except:
		return colcell, colunits, out_table, False

	# Parse the results:
	linetable = contents.split("\n")

	for line in linetable:
		# Ignore empty lines
		if len(line) > 0:
			# Check if any object was found; Simbad should return an error-message if there are none.
			if "error" in line:
				break
			elif line == "~~~":
				break
			else:
				linelist = line.split("|")
				out_table.append(linelist)

	# convert simbad cross-matched table into dataframe
	df = pd.DataFrame(out_table, columns=colcell)
	# convert dtype of otype as string
	df.otype = df.otype.astype('str')
	df.otype = [d[1:-1] for d in df.otype.values]


	df = df.sort_values('offset', ascending=1)

	# redefine colcell and out_table
	colcell = df.columns
	out_table = df.values

	# Return output, status flag indicating search success:
	return colcell, colunits, out_table, True

def tns_check(ra, dec, srad):

	# Define the TNS URL for the search.
	url = "https://wis-tns.weizmann.ac.il/search?&ra="+str(ra)+"&decl="+str(dec)+"&radius="+str(srad)+\
		  "&coords_unit=arcsec&format=csv"

	colcell = []
	colunits = []
	out_table = []

	# Try to obtain the TNS table:
	try:
		contents = requests.get(url).text

	# If the URL-request failed, we return empty tables and a status indicating search FAILURE.
	except:
		return colcell, colunits, out_table, False

	# The output (CSV) is pretty straightforward: The first line is the list of column names,
	# every other line is data. While there are many columns, the most relevant of these (for now at least)
	# are name [1], RA [2], Dec[3] and Obj.type [4].
	# All columns are comma-separated and coordinates are in sexagesimal (these will be converted for now).
	# DEV.note:
	# We also have Disc. magnitude[17] and Disc.mag filter [18], plus Disc.date [19] which are relevant
	# because these are transients. For the time being, I'm going to skip the magnitudes because there is
	# no easy way to identify the bands (these vary from case to case), and also because it could be misleading
	# because they are transients. These can be added later once implementation is a bit more clear.

	# Parse the results:
	linetable = contents.split("\n")

	# First line gives us our column names. We'll also expand our unit-list to match and add the unit-markers for
	# RA and Dec.
	colcell = linetable[0].split("\",\"")

	# Clear out the quotation marks:
	for i in range(len(colcell)):
		colcell[i] = str(colcell[i]).strip("\"")
		colunits.append("")

	colunits[2], colunits[3] = "deg", "deg"

	for line in linetable[1:]:
		linelist = line.split("\",\"")

		# Strip the quotation-marks from each element:
		for i in range(len(linelist)):
			linelist[i] = str(linelist[i]).strip("\"")

		# Convert RA and Dec:
		pos = str(linelist[2])+str(linelist[3])
		skypos = skycoord(pos, unit=(u.hourangle, u.deg))
		(linelist[2], linelist[3]) = (skypos.ra.degree, skypos.dec.degree)

		out_table.append(linelist)

	# Return filled output tables and a status flag indicating search success.
	return colcell, colunits, out_table, True

def cat_search(ra_in, dec_in, srad):
	ra_in, dec_in = float(ra_in), float(dec_in)


	# give catsHTM rootpath
	catsHTM_rootpath = par['catsHTM_rootpath']


	srad = Angle(float(srad) * u.arcsec)
	cats_srad = srad.arcsec
	# Convert center-position into Astropy SkyCoords:
	position = skycoord(ra=ra_in * u.degree, dec=dec_in * u.degree, frame="icrs")

	def get_center_offset(pos):
		# get separation between two positions
		sep_angle = pos.separation(position)
		return sep_angle.arcsec


	# all catalogs used to check
	all_catalogs = ['TMASS', 'TMASSxsc', 'AAVSO_VSX', 'AKARI', 'APASS', 'DECaLS', 'FIRST',
               'GAIADR1', 'GAIADR2', 'GALEX', 'GLADE', 'IPHAS', 'NEDz', 'PS1', 'PTFpc', 'ROSATfsc',
               'SkyMapper', 'SpecSDSS', 'SAGE', 'IRACgc', 'UCAC4', 'UKIDSS', 'VISTAviking', 'VSTkids',
               'WISE', 'XMM','simbad','tns']


	# define the result table
	useful_col = ['catname','ra','dec','offset','otype']
	all_items_df = pd.DataFrame(columns=useful_col)

	for cat in all_catalogs: # loop through all catalogs
		if cat == 'simbad':
			sb_cols, sb_units, sb_out, sb_success = simbad_check(ra=position.ra.degree, dec=position.dec.degree, srad=srad.arcsec)
			if (sb_success == 1) and (len(sb_out) > 0):
				itemframe = pd.DataFrame(sb_out, columns = sb_cols)
				itemframe['offset'] = [Angle(float(off) * u.arcsec).arcsec for off in itemframe['offset'].values]
				itemframe = itemframe[useful_col[1:]]
				itemframe[useful_col[1:-1]] = itemframe[useful_col[1:-1]].astype('float')
				itemframe['catname'] = 'simbad'
				itemframe = itemframe[useful_col]
				itemframe = itemframe.sort_values('offset', ascending=1).iloc[[0]]
				all_items_df = pd.concat([all_items_df, itemframe], axis=0)
				# if 'Galaxy' in itemframe.otype.values:
				# 	break
		elif cat == 'tns':
			tns_cols, tns_units, tns_out, tns_success = tns_check(ra=position.ra.degree, dec=position.dec.degree, srad=srad.arcsec)
			tns_cols = [tns_cols[i].lower() for i in range(len(tns_cols))]

			if tns_success == True and len(tns_out) > 0:
				itemframe = pd.DataFrame(tns_out, columns = tns_cols)
				itemframe['skycoord'] = skycoord(itemframe['ra'], itemframe['dec'], unit=u.deg, frame='icrs')
				itemframe['offset'] = itemframe['skycoord'].apply(get_center_offset)

				itemframe['otype'] = itemframe['obj. type']
				itemframe = itemframe[useful_col[1:]]
				itemframe['catname'] = 'tns'
				itemframe = itemframe[useful_col]
				itemframe = itemframe.sort_values('offset', ascending=1).iloc[[0]]
				all_items_df = pd.concat([all_items_df, itemframe], axis=0)
		else:
			# make sure the catalog name is string
			cat = str(cat)
			# cone search with catsHTM
			if not cat == 'GLADE':
				cat_out, colcell, colunits = catsHTM.cone_search(cat, position.ra.radian, position.dec.radian,
																 cats_srad, catalogs_dir=catsHTM_rootpath, verbose=False)
			else:
				cat_out, colcell, colunits = catsHTM.cone_search(cat, position.ra.radian, position.dec.radian,
																 Angle(float(30) * u.arcsec).arcsec, catalogs_dir=catsHTM_rootpath, verbose=False)

			colcell = [colcell[i].lower() for i in range(len(colcell))]
			colunits = [colunits[i].lower() for i in range(len(colunits))]
			# create dict for unit of each column
			colunits = {colcell[i]:colunits[i] for i in range(len(colcell))}
		
			if len(cat_out) > 0:
				# create empty cross-match result table if the cross-match result is not None
				itemframe = pd.DataFrame(cat_out, columns = colcell)
				# change the unit of RA and Dec as degrees
				if colunits['ra'] == 'rad' and colunits['dec'] == 'rad':
					itemframe['ra'] = itemframe['ra'].apply(degrees)
					itemframe['dec'] = itemframe['dec'].apply(degrees)
				elif colunits['ra'] == 'radians' and colunits['dec'] == 'radians':
					itemframe['ra'] = itemframe['ra'].apply(degrees)
					itemframe['dec'] = itemframe['dec'].apply(degrees)
				elif colunits['ra'] == 'deg' and colunits['dec'] == 'deg':
					itemframe['ra'] = itemframe['ra'].apply(float)
					itemframe['dec'] = itemframe['dec'].apply(float)
				# create new column for SkyCoord onjects
				itemframe['skycoord'] = skycoord(itemframe['ra'], itemframe['dec'], unit=u.deg, frame='icrs')
				# get angular difference between the cross-matched objects and the input position
				itemframe['offset'] = itemframe['skycoord'].apply(get_center_offset)
				# sort dataframe by offset
				itemframe = itemframe.sort_values('offset', ascending=1).iloc[[0]]
				# define type of the crossmatched object
				if cat == 'AAVSO_VSX':
					itemframe['otype'] = 'VS'
				elif cat == 'GLADE':
					itemframe['otype'] = 'Galaxy'
				else:
					itemframe['otype'] = 'Unknown'
				# add catalog name
				itemframe['catname'] = cat
				# select useful col only
				itemframe = itemframe[useful_col]
				all_items_df = pd.concat([all_items_df, itemframe], axis=0)

			
	if all_items_df.empty:
		return all_items_df
	else:
		all_items_df = all_items_df.sort_values('offset', ascending=1)
		all_items_df = all_items_df.reset_index().drop("index",axis=1)
		return all_items_df

if __name__ == '__main__':
	ra_in, dec_in, srad = sys.argv[1:] 
	df = cat_search(ra_in, dec_in, srad)
	print(df)

		
			

