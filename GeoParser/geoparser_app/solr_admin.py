'''
GeoParser admin core Utility
- Store information about index configuration
	- 	id - domain-name
	- 	indexes -  list of indexes for this domain.
	-	core_names - list of cores for those indexes.
	-	point_list - list of num of points points found 
	-	idx_size_list - list of size of target index
	-	idx_field_list - csv list of fields for each document
	-	count - Current count of total cores created for this domain 
	-	username - list of username for target indexes
	-	password - list of passwords for target indexes

'''

import yaml
import requests

from solr import create_core, headers, SOLR_URL, params
from keyczar_util import Crypter

ADMIN_CORE = 'admin'
'''
LIST OF FIELD START
Add all new fields in delete_index_core() which needs to be updated
'''
ADMIN_F_IDX_LIST = "indexes"
ADMIN_F_CORE_LIST = "core_names"
ADMIN_F_PNT_LEN_LIST = "point_len_list"
ADMIN_F_IDX_SIZE_LIST = "idx_size_list"
ADMIN_F_IDX_FIELD_LIST = "idx_field_list"
ADMIN_F_COUNT = "count"
ADMIN_F_USER_LIST = "username"
ADMIN_F_PASSWD_LIST = "password"
'''
LIST OF FIELD ENDS
'''
DEFAULT_IDX_FIELD = 'id,title'

'''
keyczar.Crypter object
'''
crypter = Crypter()

def _get_domain_admin(domain):
	url = '{0}{1}/select?q=id:{2}&wt=json'.format(SOLR_URL, ADMIN_CORE, domain)	
	response = requests.get(url, headers=headers)
	return yaml.safe_load(response.text)

def get_index_core(domain, index_path, user="user",passwd="pass"):
	# TODO strip trailing /
	
	if create_core(ADMIN_CORE):		
		response = _get_domain_admin(domain)
		
		num_found = response['response']['numFound']
		if(num_found == 0):  # # No record found for this domain.  
			count = 1  # # Initialize a new one
		else:
			# Check if this index exist for this domain
			all_idx = response['response']['docs'][0][ADMIN_F_IDX_LIST]
			count = response['response']['docs'][0][ADMIN_F_COUNT][0]
			if(index_path in all_idx):
				index_arr = all_idx.index(index_path)
				core_name = response['response']['docs'][0][ADMIN_F_CORE_LIST][index_arr]
				# todo encrypt it
				stored_user = response['response']['docs'][0][ADMIN_F_USER_LIST][index_arr]
				stored_passwd = response['response']['docs'][0][ADMIN_F_PASSWD_LIST][index_arr]
				# return existing core name with user name and passwprd  
				return core_name,stored_user,crypter.decrypt(stored_passwd)
			# if not create a new count for this index
			print "No existing core found for ", domain, index_path
			count = count + 1
		
		# get unique core name
		core_name = "{0}_{1}".format(domain, count)
		payload = {
					"add":{
						   "doc":{
								  "id" : "{0}".format(domain) ,
								  ADMIN_F_IDX_LIST : {"add":"{0}".format(index_path)},
								  ADMIN_F_CORE_LIST : {"add":core_name},
								  ADMIN_F_PNT_LEN_LIST : {"add":0 },
								  ADMIN_F_IDX_SIZE_LIST : {"add":0 },
								  ADMIN_F_IDX_FIELD_LIST : {"add":DEFAULT_IDX_FIELD },
								  ADMIN_F_USER_LIST: {"add":"{0}".format(user) },
								  ADMIN_F_PASSWD_LIST: {"add":"{0}".format(crypter.encrypt(passwd) ) },
								  ADMIN_F_COUNT : {"set":count }
								  }
						   }
				   }
		
		r = requests.post("{0}{1}/update".format(SOLR_URL, ADMIN_CORE), data=str(payload), params=params, headers=headers)
		
		print r.text
		if(not r.ok):
			raise "Can't create core with core name {0}".format(core_name)
			return
		
		# return newly created core
		return core_name,user,passwd

def get_all_domain_details():
	resp = {}
	if create_core(ADMIN_CORE):
		url = '{0}{1}/select?q=*&wt=json'.format(SOLR_URL, ADMIN_CORE)
		response = requests.get(url, headers=headers)
		response = yaml.safe_load(response.text)['response']['docs']
		
		for doc in response:
			resp[doc["id"]] = doc[ADMIN_F_IDX_LIST]
		
		return resp
	
def get_idx_details(domain, index_path):
	'''
	Return size of original index and number of points found till now
	'''
	if create_core(ADMIN_CORE):
		response = _get_domain_admin(domain)['response']['docs'][0]
		all_idx = response[ADMIN_F_IDX_LIST]
		if(index_path in all_idx):
			index_arr = all_idx.index(index_path)
			return response[ADMIN_F_IDX_SIZE_LIST][index_arr], response[ADMIN_F_PNT_LEN_LIST][index_arr]
			
	return 0, 0
				
			
def update_idx_details(domain, index_path, idx_size, pnt_size):
	'''
	Updates size of original index and number of points found till now
	'''
	if create_core(ADMIN_CORE):
		response = _get_domain_admin(domain)['response']['docs'][0]
		all_idx = response[ADMIN_F_IDX_LIST]
		
		if(index_path in all_idx):
			index_arr = all_idx.index(index_path)
			response[ADMIN_F_PNT_LEN_LIST][index_arr] = pnt_size
			response[ADMIN_F_IDX_SIZE_LIST][index_arr] = idx_size
			
		
		payload = {
					"add":{
						   "doc":{
								  "id" : "{0}".format(domain) ,
								  ADMIN_F_PNT_LEN_LIST : {"set":response[ADMIN_F_PNT_LEN_LIST] },
								  ADMIN_F_IDX_SIZE_LIST : {"set":response[ADMIN_F_IDX_SIZE_LIST] }
								  }
						   }
				   }
		r = requests.post("{0}{1}/update".format(SOLR_URL, ADMIN_CORE), data=str(payload), params=params, headers=headers)
		
		print r.text
		if(not r.ok):
			print payload
			raise "Can't update idx details with core name {0} - {1}".format(domain, index_path)
		
		return True
			
	return False
	
def update_idx_field_csv(domain, index_path, idx_field_csv):
	'''
	Updates field_csv from original index to be shown on popups
	'''
	if create_core(ADMIN_CORE):
		response = _get_domain_admin(domain)['response']['docs']
		if len(response) == 1:
			response = response[0]
			all_idx = response[ADMIN_F_IDX_LIST]
			
			if(index_path in all_idx):
				index_arr = all_idx.index(index_path)
				response[ADMIN_F_IDX_FIELD_LIST][index_arr] = "{0}".format(idx_field_csv)
				
			
			payload = {
						"add":{
							   "doc":{
									  "id" : "{0}".format(domain) ,
									  ADMIN_F_IDX_FIELD_LIST : {"set":response[ADMIN_F_IDX_FIELD_LIST] }
									  }
							   }
					   }
			r = requests.post("{0}{1}/update".format(SOLR_URL, ADMIN_CORE), data=str(payload), params=params, headers=headers)
			
			print r.text
			if(not r.ok):
				print payload
				raise "Can't update idx details with core name {0} - {1}".format(domain, index_path)
			
			return True
			#
	return False

def get_idx_field_csv(domain, index_path):
	'''
	Returns field_csv from original index to be shown on popups
	'''
	if create_core(ADMIN_CORE):
		response = _get_domain_admin(domain)['response']['docs'][0]
		all_idx = response[ADMIN_F_IDX_LIST]
		if(index_path in all_idx):
			index_arr = all_idx.index(index_path)
			return response[ADMIN_F_IDX_FIELD_LIST][index_arr]
			
	return 0, 0
		
def delete_index_core(domain, index_path):
	# TODO strip trailing /
	
	if create_core(ADMIN_CORE):		
		response = _get_domain_admin(domain)
		
		num_found = response['response']['numFound']
		if(num_found == 0):  # # No record found for this domain.  
			return "No domain added with name - "  + domain
		else:
			# Check if this index exist for this domain
			all_idx = response['response']['docs'][0][ADMIN_F_IDX_LIST]
			if(index_path not in all_idx):
				return "No index added with name {0} for domain {1} ".format(index_path,domain)

		index_in_arr = all_idx.index(index_path)
		
		new_doc = response['response']['docs'][0]
		print "Data now -", new_doc
		del(new_doc[ADMIN_F_IDX_LIST][index_in_arr])
		del(new_doc[ADMIN_F_CORE_LIST][index_in_arr])
		del(new_doc[ADMIN_F_PNT_LEN_LIST][index_in_arr])
		del(new_doc[ADMIN_F_IDX_SIZE_LIST][index_in_arr])
		del(new_doc[ADMIN_F_IDX_FIELD_LIST][index_in_arr])
		del(new_doc[ADMIN_F_USER_LIST][index_in_arr])
		del(new_doc[ADMIN_F_PASSWD_LIST][index_in_arr])
		
		print "Updated data - ", new_doc
			
		payload = {
					"add":{
						   "doc":new_doc
						   }
				   }
 		
		r = requests.post("{0}{1}/update".format(SOLR_URL, ADMIN_CORE), data=str(payload), params=params, headers=headers)
 		
		print r.text
		if(not r.ok):
			print "Can't delete index with name {0} for domain {1} ".format(index_path,domain)
		else:
			print "Deleted index with name {0} for domain {1} ".format(index_path,domain)
 		
		

