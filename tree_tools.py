#!/usr/bin/env python
# coding: utf-8

__all__ = [
# # ------------------- UTILS ----------------
	"tree_iterator",  #(tree) yield (path,obj)
	"tree_pred_iterator",  #(tree) yield (path,pred,k)
	"get_subtree",    #(root,path) -> obj
	"make_subdir",   #(root,path) -> obj
	"set_subtree",	  #(root,path,obj) -> None
# # --------------------- JSON UTILS --------------------
	"myjson_load",    	#(path)->obj
	"myjson_dump",    	#(obj,path)
	"myjson_dumps",   	#(obj)->str
	"json_merge",		#(to_tree,from_tree)-> None
	"strip_json_scomments",#(tree,keycom='\1comment')->tree
]

# # ------------------- UTILS ----------------

# In[6]:

def tree_iterator(tree,stopper=lambda k:False):
	"""проходится по всему дереву
	на каждом узле(листе) возвращает пару (путь, значение)
	где путь - список имен, по которым надо добираться по дереву до значения"""
	if type(tree)!=dict:
		yield (),tree
		return
	for k,v in tree.items():
		if type(v)==dict and not stopper(k):
			for path,v2 in tree_iterator(v,stopper):
				#path.insert(0,k)
				yield (k,)+path,v2
		else:
			yield (k,),v
#r = {'a':1,'b':{'c':2,'d':3}}
#for x in tree_iterator(r):
#	print(x)


def tree_pred_iterator(tree):
	"""проходится по всему дереву
	на каждом узле(листе) возвращает тройку (путь, предок, ключ)
	где путь - список имен, по которым надо добираться по дереву до значения"""
	assert type(tree)==dict
	for lk,lv in tree.items():
		if type(lv)==dict:
			for path,p,k in tree_pred_iterator(lv):
				#path.insert(0,k)
				yield (lk,)+path,p,k
		else:
			yield (lk,),tree,lk

			
# In[7]:


def get_subtree(root,path):
	"""берет корень и путь, проходит по пути, и возвращает то, где оказался"""
	#if len(path)==0: return root
	#else: return get_subtree(root[path[0]],path[1:])
	
	tmp = root
	for k in path:
		assert k in tmp, (path,k)
		tmp = tmp[k]
	return tmp
def make_subdir(root,path):
	"""берет корень и путь, проходит по пути и создает его, если его нет"""
	if len(path)==0: return root
	else: 
		if path[0] not in root: root[path[0]]={}
		return make_subdir(root[path[0]],path[1:])
def set_subtree(root,path,obj):
	tmp = make_subdir(root,path[:-1])
	tmp[path[-1]]=obj
	
# # --------------------- JSON UTILS --------------------
# In[10]:


import json, codecs

def myjson_load(path):
	"""загружаем хэши, вычисляем хэши, сохраняем хэши"""
	with codecs.open(path,'r', encoding='utf-8') as file: #, errors='surrogatepass'
		old_root = file.read()
		old_root = json.loads(old_root)
		#print('readed',path)
		#print(old_root.keys())
	return old_root

def myjson_dumps(old_root):
	return json.dumps(old_root,indent='\t',ensure_ascii=False)

def myjson_dump(old_root,path):
	try:
		print('start writing')
		with codecs.open(path,'w', encoding='utf-8') as file: #, errors='surrogatepass'
			s = myjson_dumps(old_root)
			file.write(s)
			print('writed',path)
	except Exception as e:
		print('start writing with exception',e)
		with codecs.open(path,'w', encoding='utf-8') as file: #, errors='surrogatepass'
			s = myjson_dumps(old_root)
			file.write(s)
			print('writed',path)

def json_merge(to_tree,from_tree):
	assert type(to_tree)==dict or type(to_tree)==list, type(to_tree)
	assert type(to_tree)==type(from_tree), (type(to_tree),type(from_tree))
	if type(to_tree)==dict:
		for k,v in from_tree.items():
			if k in to_tree:
				tree_merge(to_tree[k],v)
			else:
				to_tree[k] = v
	elif type(to_tree)==list:
		for v in from_tree:
			to_tree.append(v)

def strip_json_scomments(tree,keycom='\1comment'):
	if type(tree)==dict:
		if keycom in tree:
			del tree[keycom]
		for name in tree:
			tree[name] = strip_json_scomments(tree[name],keycom)
	elif type(tree)==list:
		for name in range(len(tree)):
			tree[name] = strip_json_scomments(tree[name],keycom)
	return tree
		
