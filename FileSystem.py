#!/usr/bin/env python
# coding: utf-8

# # сканирование, и подсчет хешей

# проверка на симлинки
# стандартная проверка в windows junction-ы не считает симлинками

__all__ = [
# # ------------------- UTILS ----------------
	"normalize_path",		#(s):
	"case_normalize_path",	#(s):
	# seq - tuple or list
	# path - sequence of str
	"my_path_join_a", #(*seq)->str
	"my_path_join_l", #(seq)->str
	"is_subpath",     #(long_path,short_path)->bool
	#сжатие путей и файлов в одну строку
	"nested_join",    	#(root,splitter='/')->root
	"nested_split",   	#(root,splitter='/')->root
	#деревья <-> списки
	"pathlist2tree",	#(ll,ender='\0')->tree
	"tree2pathlist",	#(tree,ender='\0')->ll
	#слияние деревьев
	"tree_join",		#(dict_tree,ender='\0')->tree
	"tree_split",		#(tree,ender='\0')->dict_tree
# # ------------------- SCAN ------------------------
	"scan",           #(rootpath,exceptions=set())->file_tree
	"calc_hashes",    #(->root,old_root,prefix)
	"tree_stat",      #(tree) -> (size, dirs, files, bad_files)
	"tree_select",    #(tree,pred) -> tree
# # ------------------- DIFF --------------
	"first_diff",     #(old_root,root) -> True or (path,(old,new))
	"path_diff",      #(old_root,root) -> (modified,old,new,strict_old,strict_new,touched)
	"hash_diff1",      #(old,new)       -> (moved,old_dirs,new_dirs,old,new)
# # ---------------------- PATCH, SYNC -------------------------
	"path_patch1",     #(old_root,modified,old,new, touched = {}) -> new_root
	"hash_patch",     #(old_root,modified,moved,old_dirs,new_dirs,old,new, touched={}) -> new_root
	"path_back_patch1",
	"hash_back_patch",#(new_root,modified,moved,old_dirs,new_dirs,old,new, touched={}) -> old_root
	# path_sync
	# hash_sync

	"path_patch",		#(olderrors,modified,old,new,strict_old,strict_new,touched):
	"path_back_patch",	#(olderrors,modified,old,new,strict_old,strict_new,touched):
	"hash_diff",		#(oldroot_d,root_d):
# # --------------------- DUMP LOAD --------------------
	# + сортировка по путям (комментами)
	"fileinfo_compress",#(list)->str
	"fileinfo_uncompress",#(str)->list
	"path_patch_dump",	#(modified      ,old,new,strict_old,strict_new,touched)->obj
	"hash_patch_dump",	#(modified,moved,old_dirs,new_dirs,old,new    ,touched)->obj
	"path_patch_load",	#obj->(modified      ,old,new,strict_old,strict_new,touched)
	"hash_patch_load",	#obj->(modified,moved,old_dirs,new_dirs,old,new    ,touched)
	"action2tree",
	"tree2action",
	"moved2pathlist",
	"pathlist2moved",
	"statistics",
	"path_patch_compress",	#(modified      ,old,new,strict_old,strict_new,touched)->obj
	"hash_patch_compress",	#(modified,moved,old_dirs,new_dirs,old,new    ,touched)->obj
	"path_patch_uncompress",	#obj->(modified      ,old,new,strict_old,strict_new,touched)
	"hash_patch_uncompress",	#obj->(modified,moved,old_dirs,new_dirs,old,new    ,touched)
	"load_snapshot",	#(path):
	"dump_snapshot",	#(errors,root,path):
# # --------------------- PATCH CHEIN --------------------
	"diff",				#(old_snap,new_snap):
	"patch_chain",		#(lst,frm,to,in_snapshot):
	"check_list",		#(path='.',start = None):
]


def DT_EQ(t1,t2):
	t1s = str(t1)
	t2s = str(t2)
	t11 = float(t1s[:min(len(t1s),len(t2s))])
	t22 = float(t2s[:min(len(t1s),len(t2s))])
	DT = 1 # 1 second between timestamps
	if t11==t22: return True
	if abs(t11-t22)<DT: print('too small time delta',t11,t22,'(',t1,t2,')')
	return False

# # ------------------- UTILS ----------------
# In[3]:


# прогресс-бар числом - для случаев while и т.п.
from ipywidgets import HTML
from IPython.display import display
from time import sleep
from tree_tools import *
#label = HTML()
#display(label)
#for x in range(10):
#	label.value = str(x)
#	sleep(0.1)

def normalize_path(s):
	from_pat = re.escape(os.sep+os.sep)+'|'+\
		re.escape(os.sep+'/')+'|'+\
		re.escape('/'+os.sep)+'|'+\
		re.escape('//')
	to_pat = '/'
	while re.search(from_pat,s):
		s = re.sub(from_pat,to_pat,s)
	return s
def case_normalize_path(s):
	s = normalize_path(s)
	if os.name=='nt':
		s.upper()
	return s
	
# In[4]:

import os
from stat import *

def slash_replacer(s):
	while s[0]==os.sep:
		s = s[1:]
	while s[-1]==os.sep:
		s = s[:-1]
	return s
def my_path_join_a(*ll):
	return os.sep.join([slash_replacer(s) for s in ll])
def my_path_join_l(ll):
	return os.sep.join([slash_replacer(s) for s in ll])
#my_path_join_a('a:\\c\\','b')


def is_subpath(subpath,path):
	"""сначала длинный, потом короткий"""
	if len(subpath)<len(path):
		return False
	for i in range(len(path)):
		if subpath[i]!=path[i]:
			return False
	return True

def fileinfo_compress(root):
	assert type(root)==list
	return str(root[0])+' '+str(root[1])+' '+str(root[2])
	# root[2] обычно строка, но иногда это None

def fileinfo_uncompress(root):
	assert type(root)==str
	# root[2] обычно строка, но иногда это None
	root = root.split(' ')
	root[0] = None if root[0]=='None' else float(root[0])
	root[1] = None if root[1]=='None' else int(root[1])
	if root[2]=='None': root[2]=None
	return root


# In[18]:
def nested_join(root,splitter='/',stopper=lambda k:False,leaf_handler=fileinfo_compress):
	"""поддеревья, в которых содержится один элемент преобразовывает...
	типа {'a':{'b':1,'c':2,'d':3}} -> {'a/b':1,'a/c':2,'a/d':3}
	"""
	if type(root)==dict:
		new_root = {}
		for name in root.keys():
			assert type(name)==str, name
			tmp_root = root
			name_path = name
			while type(tmp_root[name])==dict and len(tmp_root[name])==1 and \
					not stopper(next(iter(tmp_root[name]))):
				subname = next(iter(tmp_root[name]))
				assert type(subname)==str
				tmp_root = tmp_root[name]
				name_path+=splitter+subname
				name = subname
			new_root[name_path] = nested_join(tmp_root[name],splitter,stopper,leaf_handler)
		return new_root
	else:
		return leaf_handler(root)


# In[19]:


#nested_join({
#	'x':{
#		'y':[1,2,'3'],
#		#'z':[1,2,'3'],
#	}
#})


# In[35]:


def nested_split(root,splitter='/',del_splitter=True,stopper=lambda k:False,leaf_handler=fileinfo_uncompress):
	if type(root)==dict:
		new_root = {}
		for name in root.keys():
			assert type(name)==str, name
			if stopper(name):
				new_root[name] = root[name]
			else:
				tmp = nested_split(root[name],splitter,del_splitter,stopper,leaf_handler)
				tmp_name = tuple(name.split(splitter))
				if not del_splitter:
					if tmp_name[0]=='': tmp_name=tmp_name[1:]
					tmp_name = tuple(splitter+x for x in tmp_name)
				while len(tmp_name)>1:
					tmp = {tmp_name[-1]:tmp}
					tmp_name = tmp_name[:-1]
				new_root[tmp_name[0]] = tmp
		return new_root
	else:
		return leaf_handler(root)

def pathlist2tree(ll,ender='\0'):
	if next(iter(ll)).startswith(ender): return ll
	tree = {}
	for p,v in ll.items():
		p1=(ender+p[0],*p[1:-1],p[-1]+ender) if len(p)>1 else (ender+p[0]+ender,)
		set_subtree(tree,p1,v)
	return tree

def tree2pathlist(tree,ender='\0'):
	if not next(iter(tree)).startswith(ender): return tree
	ll={}
	for p,v in tree_iterator(tree,lambda k:k.endswith(ender)):
		if len(p)>1: ll[(p[0][len(ender):],)+p[1:-1]+(p[-1][:-len(ender)],)] = v
		else:        ll[(p[0][len(ender):-len(ender)],)] = v
	return ll

def tree_join(dict_tree,ender='\0'):
	tree = {}
	for tree_name,cur_tree in dict_tree.items():
		for p,v in tree_iterator(cur_tree,lambda k:k.endswith(ender)):
			assert p[0].startswith(ender)
			p1=(ender+p[0],*p[1:-1],p[-1]+tree_name) if len(p)>1 else (ender+p[0]+tree_name,)
			set_tree(tree,p1,v)
	return tree

import re

def tree_split(tree,ender='\0'):
	if not next(iter(tree)).startswith(ender+ender): return tree
	tree_dict = {}
	def end_checker(k):
		tmp = re.match('.*'+ender,k)
		if tmp: return tmp.start()!=0
		else: return False
	for p,v in tree_iterator(tree,end_checker(k)):
		assert p[0].startswith(ender)
		tree_name = p[-1].split(ender)[1]
		if len(p)>1: p1 = (p[0][len(ender):],)+p[1:-1]+(p[-1].split(ender)[0]+ender,)
		else:        p1 = (p[0].split(ender)[2]+ender,)
		set_tree(tree_dict[tree_name],p1,v)
	return tree_dict
	
		
# # ------------------- SCAN ------------------------
# In[2]:

if os.name=='nt':
	from ctypes import *
	from ctypes.wintypes import *

	FILE_ATTRIBUTE_REPARSE_POINT = 0x00400
	INVALID_FILE_ATTRIBUTES = 0xFFFFFFFF

	kernel32 = WinDLL('kernel32')
	GetFileAttributesW = kernel32.GetFileAttributesW
	GetFileAttributesW.restype = DWORD
	GetFileAttributesW.argtypes = (LPCWSTR,) #lpFileName In

	def is_winlink(path):
		result = GetFileAttributesW(path)
		if result == INVALID_FILE_ATTRIBUTES:
			raise OSError((path,WinError()))
		return bool(result & FILE_ATTRIBUTE_REPARSE_POINT)
elif os.name=='posix':
	def is_winlink(path):
		return False
else:
	raise Exception('unknown OS name: '+os.name)

#is_winlink(r'D:\Users\feelus\Local Settings')


# In[5]:

import codecs
def my_eh_suresc_s2b(err):
    if err.reason == 'surrogates not allowed':
        return (repr(err.object[err.start:err.end])[1:-1],err.end)
    else:
        return codecs.strict_errors(err)
codecs.register_error('my_eh_suresc_s2b', my_eh_suresc_s2b)
def suresc(s):
    obj = codecs.encode(s, encoding='utf-8', errors='my_eh_suresc_s2b')
    return codecs.decode(obj,encoding='utf-8')
	
def scan(rootpath,exceptions=set()):
	total_size = 0
	ts_printed = 0
	
	exc1 = set()
	for n in exceptions:
		exc1.add(case_normalize_path(n))
	exceptions = exc1

	#label = HTML()
	#display(label)
	errors = {}
	def append(root,path,val):
		path = path[len(rootpath):].split(os.sep)
		set_subtree(root,path,val)

	def scan1(curpath):
		nonlocal total_size
		nonlocal ts_printed
		if case_normalize_path(curpath) in exceptions:
			return {}
		curroot = {}
		#print(curpath)
		try:
			with os.scandir(curpath) as it:
				for entry in it:
					try:
						name = suresc(entry.name)
						if name!='.' and name!='..' and \
						 not entry.is_symlink() and not is_winlink(entry.path):
							if entry.is_dir(follow_symlinks=False):
								curroot[name] = scan1(entry.path)
							elif entry.is_file(follow_symlinks=False):
								st = entry.stat(follow_symlinks=False)
								curroot[name] = [st.st_mtime,st.st_size]
								total_size+=st.st_size
							else:
								#print('unknown object:',entry.path)
								append(errors,suresc(entry.path),[-1,-1,None])
					except OSError as e:
						#print(curpath+os.sep+entry.name)
						append(errors,suresc(curpath)+os.sep+name,[-1,-1,None])
						#print(e)
						#print()
		except OSError as e:
			#print(curpath+os.sep)
			append(errors,suresc(curpath),{})
			#print(e)
			#print()
			return {}
		if ts_printed<int(total_size/1024/1024/1024):
			ts_printed = int(total_size/1024/1024/1024)
			#label.value = str(ts_printed)+' GB scanned'
			print(str(ts_printed)+' GB scanned',end='\r')
		return curroot
	tmp = scan1(rootpath)
	#label.value = str(ts_printed)+' GB scanned - completed'
	print(str(ts_printed)+' GB scanned - completed')
	return tmp, errors


# In[8]:


import hashlib
def md5(fname):
	"""вычисляет хеш файла по его пути"""
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()


# In[9]:


def calc_hashes(root,errors,old_root,prefix):
	total_size = 0
	calc_size = 0
	ts_printed = 0
	#label = HTML()
	def calc_hashes1(root,old_root,path):
		nonlocal total_size
		nonlocal ts_printed
		nonlocal calc_size
		
		for name in root.keys():
			if type(root[name])==dict: # directory
				if name in old_root and type(old_root[name])==dict:
					calc_hashes1(root[name],old_root[name],path+(name,))
				else:
					calc_hashes1(root[name],{},path+(name,))
			elif type(root[name])==list: # file
				assert len(root[name])>=2
				if name in old_root and type(old_root[name])==list and	\
				  len(old_root[name])>=3 and root[name][1]==old_root[name][1] and \
				  DT_EQ(root[name][0],old_root[name][0]): # 1 second between timestamps
					if len(root[name])==2:
						root[name].append(old_root[name][2])
					else:
						root[name][2] = old_root[name][2]
				else:
					p = my_path_join_a(prefix,*path,name)
					try:
						#print(p)
						st = os.stat(p)  # зависает при чтении некоторых файлов
										# stat от этих файлов будет ошибкой
						root[name][0] = st.st_mtime # update
						root[name][1] = st.st_size # update
						if len(root[name])==2:
							root[name].append(md5(p))
						else:
							root[name][2] = md5(p)
					except OSError as e:
						if len(root[name])==2:
							root[name].append(None)
						#print(p)
						set_subtree(errors,path+(name,),root[name])
						#print(e)
						#print()
					assert type(root[name][1]) == int, path+(name,)
					calc_size+=root[name][1]
				if type(root[name][1])==int:
					total_size+=root[name][1]
				if ts_printed<int(total_size/1024/1024/1024):
					ts_printed = int(total_size/1024/1024/1024)
					#label.value = str(ts_printed)+' GB total, '+\
					#	str(int(calc_size/1024/1024/1024))+' GB calculated ('+str(int(100*calc_size/total_size))+'%)'
					print(str(ts_printed)+' GB total, '+\
						str(int(calc_size/1024/1024/1024))+' GB calculated ('\
						+str(int(100 - 100*calc_size/total_size))+'% cached)',end='\r')
			else:
				raise Exception(path)
	if old_root!={} and len(root.keys()&old_root.keys())==0:
		print('intersection root and old_root is void, do nothng, check old_root')
	else:
		if old_root=={} : print('calculating from scatch')
		#display(label)
		calc_hashes1(root,old_root,())
		#label.value = str(ts_printed)+' GB calculated, '+\
		#	str(int(calc_size/1024/1024/1024))+' GB calculated ('+str(int(100*calc_size/total_size))+'%)- completed'
		print(str(ts_printed)+' GB calculated, '\
			+str(int(calc_size/1024/1024/1024))+' GB calculated ('\
			+str(int(100 - 100*calc_size/total_size))+'% cached)- completed')


def tree_stat(tree):
	if type(tree)==list:
		if len(tree)<3 or tree[2]==None:
			return (tree[1],0,1,1)
		else:
			return (tree[1],0,1,0)
	elif type(tree)==dict:
		size = 0
		dirs = 1
		files = 0
		bad_files = 0
		for k,v in tree.items():
			(s,d,f,b) = tree_stat(v)
			size+=s
			dirs+=d
			files+=f
			bad_files+=b
		return 	(size, dirs, files, bad_files)

	else: raise Exception()

def tree_select(tree,pred):
	"""оставляет листья, удовлетворяющие предикату"""
	assert type(tree)==dict
	new_tree = {}
	for k,v in tree.items():
		if type(v)==list:
			if pred(v):
				new_tree[k]=v
		else:
			tmp = tree_select(v,pred)
			if len(tmp)>0:
				new_tree[k]=tmp
	return new_tree
	
# # ------------------- DIFF --------------

def first_diff(old_root,root):
	"""сравнивает 2 дерева файлов
	если они равны - возвращает True
	иначе находит первое различие и возвращает путь и пару элементов
	"""
	#if root==old_root:				   return True
	if type(root)!=type(old_root):	   return ((),(old_root,root))
	if type(root)==list:
		if root[1]==old_root[1] and root[2]==old_root[2]:
										 return True
		else:							return ((),(old_root,root))
	if type(root)==dict:
		if root.keys()!=old_root.keys(): return ((),(old_root.keys()-root.keys(),
													 root.keys()-old_root.keys()))
		for k in root:
			d = first_diff(old_root[k],root[k])
			if d!=True:				  return ((k,*d[0]),d[1])
	return True

# In[11]:


def path_diff(old_root,root):
	""" Сравнивает 2 дерева, возвращает словари путь:файл/папка
		modified, - модифицированные файлы
		old, - файлы и папки, которые присутствуют только в старом дереве
		new, - файлы и папки, которые присутствуют только в новом дереве
		strict_old, 
		strict_new - файлы, которые превратились в папки, и папки, которые превратились в файлы,
			strict_old - из старого дерева (файл или папка)
			strict_new - из нового дерева (файл или папка)
		touched - файлы, у которых изменилось только время доступа
	"""
	new = {}
	old = {}
	strict_new = {}
	strict_old = {}
	modified = {}
	touched = {}
	def diff1(root,old_root,path):
		#nonlocal new
		#nonlocal old
		#nonlocal modified
		#nonlocal touched
		for name in root.keys():
			path_name = path+(name,)
			if type(root[name])==dict: # directory
				if name in old_root and type(old_root[name])==dict:
					# same dirs
					diff1(root[name],old_root[name],path_name)
				elif name in old_root and type(old_root[name])==list:
					# file -> dir
					print('warning: file->dir :',my_path_join_a(*path_name))
					strict_old[path_name] = old_root[name]
					strict_new[path_name] =	 root[name]
				elif name in old_root:
					raise Exception(path_name)
				else:
					# new dir
					new[path_name] =	 root[name]
			elif type(root[name])==list: # file
				assert len(root[name])==3
				if name in old_root and type(old_root[name])==list:
					# file -> file
					assert len(old_root[name])==3
					if root[name][2]!=None and root[name][2]==old_root[name][2]:
						# same files
						assert root[name][1]==old_root[name][1], ('different sizes', path_name, root[name][1], old_root[name][1])
						if not DT_EQ(root[name][0],old_root[name][0]):
							touched[path_name] = (old_root[name], root[name])
					elif root[name][2]==None and root[name][2]==old_root[name][2] and \
					  root[name][1]==old_root[name][1] and DT_EQ(root[name][0],old_root[name][0]): # 1 second between timestamps
						# same files without hashes
						assert root[name][1]==old_root[name][1], path_name
						if not DT_EQ(root[name][0],old_root[name][0]):
							touched[path_name] = (old_root[name], root[name])
					else:
						# diff files
						modified[path_name] = (old_root[name], root[name])
				elif name in old_root and type(old_root[name])==dict:
					# dir -> file
					print('warning: dir->file :',my_path_join_a(*path_name))
					strict_new[path_name] =	 root[name]
					strict_old[path_name] = old_root[name]
				elif name in old_root:
					raise Exception(path_name)
				else:
					# new file
					new[path_name] =	 root[name]
			else:
				raise Exception(path_name)
		for name in old_root.keys():
			path_name = path+(name,)
			if name not in root:
				if type(old_root[name])==dict:
					# old dir
					old[path_name] = old_root[name]
				elif type(old_root[name])==list:
					# old file
					old[path_name] = old_root[name]
				else:
					raise Exception(path_name)
	diff1(root,old_root,())
	return (modified,old,new,strict_old,strict_new,touched)


# In[12]:


from copy import *

nest = 0

def print_lines(arg,caption=None):
	#global nest
	if caption!=None:
		print('  '*nest,caption)
	for x in arg:
		print('  '*nest,x)

verbose = 0
# 1 - стадии
# 2 - изменения
# 3 - пометки
# 4 - более детально
def vprint(v,*args):
	if verbose>=v: print(*args)
# move_obj(forced,path,subtree,variants):
# find_moved(forced,prefix_path,subtree):
def dvr(fun):
	def wrapper(*args):
		global nest
		print('  '*nest+fun.__name__+':{',args[1])
		try:
			nest+=1
			tmp = fun(*args)
		finally:
			nest-=1
		if tmp!=None and tmp!=set():
			print('  '*nest+'} find_moved','[')
			nest+=1
			if type(tmp)!=set or type(tmp)!=dict:
				print('  '*nest,tmp)
			else:
				print_lines(tmp)
			nest-=1
			print('  '*nest+']')
		return tmp
	return wrapper
	

# In[14]:


CHANGED = 1
CANDIDATES = 2
#@dvr
def del_files_by_tree(files,prefix,subtree):
	"""удаляет из files все файлы, перечисленные в subtree
	prefix - путь к subtree
	"""
	if type(subtree)==list:
		assert subtree[2] in files, subtree[2]
		assert prefix in files[subtree[2]], (prefix,files[subtree[2]])
		#print('del hash',subtree[2])
		files[subtree[2]].remove(prefix)
		if len(files[subtree[2]])==0:
			del files[subtree[2]]
	else:
		for name in subtree.keys():
			if type(name)==str:
				del_files_by_tree(files,prefix+(name,),subtree[name])

def check_variants(variants,new,names):
	# variants - список путей, куда можно переместить данный объект
	# names - 
	vars2 = set()
	for p in variants: # по каждому варианту
		for i in range(1,len(p)+1): # находим дерево в new, в котором находится данный путь
			if p[:i] in new:
				break
		else: i=None # !!! такого вообще не должно быть
		if i==None:
			continue # не добавляем в vars2
		new_tree = get_subtree(new[p[:i]],p[i:])
		# !!! может оказаться файлом а не папкой, но не должно
		# проверяем, все ли объекты внутри этой папки содержатся внутри текущей папки
		for n1 in new_tree.keys():
			if type(n1)==str and n1 not in names:
				break # не добавляем в vars2
		else:
			vars2.add(p)
	return vars2


# In[15]:


def make_moved(old_files,new_files,old,new,verbose):
	moved = []
	changed = True
	#@dvr
	def find_moved(forced,prefix_path,subtree):
		"""возвращает список путей, куда можно переместить данный объект,
		предварительно узнав, куда можно переместить все дочерние объекты
		если данный объект никуда переместить нельзя
			перемещает все вложенные объекты
		forced - передается в move_obj
		prefix_path - путь к данный объекту
		subtree - данный объект
		"""
		if type(subtree)==list:
			if subtree[2]!=None and subtree[2] in new_files:
				return new_files[subtree[2]] # ? copy - не нужно, т.к. (1)
			else: return set()
		elif type(subtree)==dict:
			# смотрим закэшированное
			if CHANGED not in subtree and CANDIDATES in subtree:
				vars2 = check_variants(subtree[CANDIDATES],new,subtree)
				if len(vars2)>0:
					return vars2 # да, эту папку куда-то целиком переместить можно

			# сначала проверяем, можно ли эту папку целиком куда-то переместить
			variants = None if CHANGED in subtree else set()
			names = {}
			for name in subtree.keys():
				if type(name)==str:
					v = find_moved(forced,prefix_path+(name,),subtree[name])
					names[name] = v
					if v == None or variants==None:
						variants = None
					else:
						v = {p[:-1] for p in v if p[-1]==name} #(1)
						variants &= v
			if variants!=None and len(variants)>0:
				# содержимое этой папки куда-то в одно место переместить можно
				# но...
				vars2 = check_variants(variants,new,names)
				if len(vars2)>0:
					return vars2 # да, эту папку куда-то целиком переместить можно

			# если же целиком эту папку никуда переместить нельзя
			# то начинаем определять, куда переместить ее содержимое
			subtree[CHANGED] = True
			#print('CHANGED',prefix_path)
			fordel = set()
			for name in subtree.keys():
				if type(name)==str:
					variants = names[name]
					if move_obj(forced,prefix_path+(name,),subtree[name],variants):
						fordel.add(name)
			for name in fordel:
				del subtree[name]
			return None
		else: raise Exception(prefix_path)
	#@dvr
	def move_obj(forced,path,subtree,variants):
		"""организует перемещение данного объекта, и возвращает, удалось ли это сделать
		если forced==False - перемещает, только если есть единственный вариант
		если forced==True - перемещает, если есть хотябы какой-то вариант
		variants - варианты перемещения
		path - путь к данному объекту
		subtree - данный объект
		"""
		nonlocal changed
		#nonlocal moved
		if variants!=None and len(variants)>1 and not forced:
			# несколько вариантов - кэшируем их в CANDIDATES
			if type(subtree)==dict:
				subtree[CANDIDATES] = variants
			return False
		elif variants!=None and (len(variants)==1 or len(variants)>0 and forced):
			# перемещаем
			changed = True
			if forced and len(variants)>1:
				for i in range(1,len(path)+1): # отсеиваем несовпадающие с конца (с таким же названием)
					tmp = {v for v in variants if i<=len(v) and v[-i]==path[-i]}
					if len(tmp)==0:
						break
					variants = tmp
				for i in range(len(path)): # отсеиваем несовпадающие с начала (в той же папке)
					tmp = {v for v in variants if i<len(v) and v[i]==path[i]}
					if len(tmp)==0:
						break
					variants = tmp
				if verbose>=2 and len(variants)>1:
					print('random move','/'.join(path))
					for v in variants:
						print('           ','/'.join(v))
			dest_p = next(iter(variants))
			# удаляем из old и old_files
			from_obj = deepcopy(subtree)
			del_files_by_tree(old_files,path,subtree)
			#fordel.add(name) -> return True
			# удаляем из new и new_files
			for i in range(1,len(dest_p)+1):
				if dest_p[:i] in new:
					break
			else: raise Exception(path)
			if len(dest_p)==i:
				to_obj = deepcopy(new[dest_p])
				del_files_by_tree(new_files,dest_p,new[dest_p])
				del new[dest_p]
			else:
				#print(dest_p[:i],dest_p[i:],dest_p[i:-1],dest_p[-1])
				#('Users', 'feelus', 'Repos', 'zadrotstvo', 'learning_science') 
				#('сто-объяснялка',) 
				#() 
				#сто-объяснялка
				dest_parent = get_subtree(new[dest_p[:i]],dest_p[i:-1])
				#print(dest_parent.keys())
				to_obj = deepcopy(dest_parent[dest_p[-1]])
				del_files_by_tree(new_files,dest_p,dest_parent[dest_p[-1]])
				del dest_parent[dest_p[-1]]
				# помечаю как CHANGED целевую папку и все ее родительские
				tmp = new[dest_p[:i]]
				tmp[CHANGED]=True
				#print('CHANGED',dest_p[:i])
				for k in range(len(dest_p[i:-1])):
					assert dest_p[i+k] in tmp, Exception((dest_p,i+k))
					tmp = tmp[dest_p[i+k]]
					tmp[CHANGED]=True
					#print('CHANGED',dest_p[:i+k+1])
				#dest_parent[CHANGED]=True
				#print('CHANGED',dest_p[:-1])
			moved.append((path,dest_p,from_obj,to_obj))
			return True
		else:
			# оставляем как есть
			return False

	# перемещаем, если это можно сделать единственным образом
	while changed:
		if verbose>=1: print('--- ITERATION ---')
		changed = False
		fordel = set()
		for p1,subtree in old.items():
			variants = find_moved(False,p1,subtree)
			if move_obj(False,p1,old[p1],variants):
				fordel.add(p1)
		for p1 in fordel:
			del old[p1]

	# перемещаем куда попало
	if 1:
		if verbose>=1: print('--- FINAL ITERATION ---')
		fordel = set()
		for p1,subtree in old.items():
			variants = find_moved(True,p1,subtree)
			if move_obj(True,p1,old[p1],variants):
				fordel.add(p1)
		for p1 in fordel:
			del old[p1]
	return moved


# In[16]:


def hash_diff1(old,new,verbose=1):
	# копирую old, new
	# создаю old_files, new_files
	# создаю moved, обходя и меняя old и new (несколько раз) (а также old_files и new_files)
	# проверяю пересечение old_files и new_files
	# раскладываю old, создаю old1, проверяю old_files
	# раскладываю new, создаю new1, проверяю new_files
	# возвращаю moved, old, new, old1, new1
	#	 old, new - содержат папки для создания и удаления перед и после перемещением

	# копирую old, new
	old = deepcopy(old)
	new = deepcopy(new)

	# создаю old_files, new_files
	def make_files(old):
		old_files = {}
		for p1,subtree in old.items():
			for p2,v in tree_iterator(subtree):
				if v[2] not in old_files:
					old_files[v[2]] = set()
				#print(p1,p2,tuple(p2))#,p1+tuple(p2))
				old_files[v[2]].add(p1+p2)
		return old_files
	# словари хэш:путь
	old_files = make_files(old)
	new_files = make_files(new)

	#print('old_files before:',old_files)
	#print('new_files before:',new_files)
	#print_lines(old.keys(),'--- old.keys ---')
	#print_lines(new.keys(),'--- new.keys ---')
	#print_lines(old.items(),'--- old.items ---')
	#print_lines(new.items(),'--- new.items ---')
	#print_lines(old_files.items(),'--- old_files ---')
	#print_lines(new_files.items(),'--- new_files ---')

	# создаю moved, обходя и меняя old и new (несколько раз) (а также old_files и new_files)
	moved = make_moved(old_files,new_files,old,new,verbose)

	#print('old_files after:',old_files)
	#print('new_files after:',new_files)
	#print('-------')
	#print(myjson_dumps(nested_join(new)))
	#print('-------')
	#print_lines(moved,'--- moved ---')
	#print_lines(old.keys(),'--- old.keys ---')
	#print_lines(new.keys(),'--- new.keys ---')
	#print_lines(old_files.items(),'--- old_files ---')
	#print_lines(new_files.items(),'--- new_files ---')

	# проверяю пересечение old_files и new_files
	#print('--- checking ---')
	flag = False
	for h1 in old_files:
		if h1!=None and h1 in new_files:
			flag = True
			#print(h1)
	if flag:
		raise Exception(h1)

	# раскладываю old, создаю old1, проверяю old_files
		# целиковые папки остануться целиковыми, их не нужно снова конструировать
	def clear_dir(files,prefix,path,subtree):
		"""вызывается от директории
		очищает директорию от CANDIDATES
		файлы удаляет из files
		"""
		if CANDIDATES in subtree: del subtree[CANDIDATES]
		#if CHANGED in subtree: del subtree[CHANGED]
		for name in subtree:
			if type(subtree[name])==list:
				assert subtree[name][2] in files, (subtree[name][2],prefix,path)
				files[subtree[name][2]].remove(prefix+path+(name,))
				if len(files[subtree[name][2]])==0:
					del files[subtree[name][2]]
			elif type(subtree[name])==dict:
				clear_dir(files,prefix,path+(name,),subtree[name])
			else:
				raise Exception((prefix,path,name,type(subtree[name])))

	def q_need_move(files,old1,prefix,path,subtree):
		"""вызывается от директории или файла
		если это файл или целикова директория - возвращает True и перемещает в old1
		очищает директоию от CHANGED, 
		файлы удаляет из files
		директории очищает
		"""
		if type(subtree)==list:
			assert subtree[2] in files, (subtree[2],prefix,path)
			files[subtree[2]].remove(prefix+path)
			if len(files[subtree[2]])==0:
				del files[subtree[2]]
			return True
		elif CHANGED not in subtree:
			clear_dir(files,prefix,path,subtree)
			return True
		else:
			del subtree[CHANGED]
			fordel = set()
			for name in subtree:
				if q_need_move(files,old1,prefix,path+(name,),subtree[name]):
					old1[prefix+path+(name,)] = subtree[name]
					fordel.add(name)
			for name in fordel:
				del subtree[name]
			return False

	old1 = {}
	fordel = set()
	for p1,subdir in old.items():
		if q_need_move(old_files,old1,p1,(),subdir):
			old1[p1] = subdir
			fordel.add(p1)
	for name in fordel:
		del old[name]
	assert len(old_files)==0

	# раскладываю new, создаю new1, проверяю new_files
	new1 = {}
	fordel = set()
	for p1,subdir in new.items():
		if q_need_move(new_files,new1,p1,(),subdir):
			new1[p1] = subdir
			fordel.add(p1)
	for name in fordel:
		del new[name]
	assert len(new_files)==0

	# возвращаю moved, old1, new1
	return (moved,old,new,old1,new1)


# In[47]:
# # ---------------------- PATCH -------------------------


# перед применением рекомендуется:
#   проверить, что old и strict_old не пересекаются (по ключам) и объединить их
#   проверить, что new и strict_new не пересекаются (по ключам) и объединить их
def path_patch1(old_root,modified,old,new, touched = {}):
	# по всем modified
	#   проверяем, что имеется по старому пути
	#   и заменяем на новое значение (через parent)
	# по всем old
	#   проверяем, что имеется по старому пути
	#   и удаляем это (через parent)
	# по всем new
	#   создаем это (через parent)
	root = deepcopy(old_root)
	for path,(old_file,new_file) in modified.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == old_file, (path,(parent[path[-1]],old_file,new_file))
		parent[path[-1]] = deepcopy(new_file)
	for path,(old_file,new_file) in touched.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == old_file, (path,(parent[path[-1]],old_file,new_file))
		parent[path[-1]] = deepcopy(new_file)
	for path,obj in old.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == obj, (path,(parent[path[-1]],obj))
		del parent[path[-1]]
	for path,obj in new.items():
		parent = get_subtree(root,path[:-1])
		assert path[-1] not in parent, (path,obj)
		parent[path[-1]] = deepcopy(obj)
	return root

def path_back_patch1(old_root,in_modified,old,new, in_touched = {}):
	modified = {}
	for path,v in in_modified.items():
		modified[path] = (v[1],v[0])
	touched = {}
	for path,v in in_touched.items():
		touched[path] = (v[1],v[0])
	return path_patch1(old_root,modified,new,old,touched)

# In[46]:


def hash_patch(old_root,modified,moved,old_dirs,new_dirs,old,new, touched={}):
	# всё модифицируем
	# всё удаляем
	# создаём все новые папки
	# всё перемещаем
	# удаляем все старые папки
	# всё создаем
	root = deepcopy(old_root)
	# всё модифицируем
	for path,(old_file,new_file) in modified.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == old_file, path
		parent[path[-1]] = deepcopy(new_file)
	for path,(old_file,new_file) in touched.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == old_file, path
		parent[path[-1]] = deepcopy(new_file)
	# всё удаляем
	for path,obj in old.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == obj, path
		del parent[path[-1]]
	# создаём все новые папки
	for path,obj in new_dirs.items():
		parent = get_subtree(root,path[:-1])
		assert path[-1] not in parent, path
		parent[path[-1]] = deepcopy(obj)
	# всё перемещаем
	for from_p,to_p,from_obj,to_obj in moved:
		parent = get_subtree(root,from_p[:-1])
		assert parent[from_p[-1]] == from_obj, from_p
		del parent[from_p[-1]]
		
		parent = get_subtree(root,to_p[:-1])
		assert to_p[-1] not in parent, to_p
		parent[to_p[-1]] = deepcopy(to_obj)
	# удаляем все старые папки
	for path,obj in old_dirs.items():
		parent = get_subtree(root,path[:-1])
		assert parent[path[-1]] == obj, path
		del parent[path[-1]]
	# всё создаем
	for path,obj in new.items():
		parent = get_subtree(root,path[:-1])
		assert path[-1] not in parent, path
		parent[path[-1]] = deepcopy(obj)
	return root

def hash_back_patch(root,in_modified,in_moved,in_old_dirs,in_new_dirs,in_old,in_new,in_touched={}):
	modified = {}
	for path,v in in_modified.items():
		modified[path] = (v[1],v[0])
	touched = {}
	for path,v in in_touched.items():
		touched[path] = (v[1],v[0])
	moved = []
	for from_p,to_p,from_obj,to_obj in in_moved:
		moved.append((to_p,from_p,to_obj,from_obj))
	return hash_patch(root,modified,moved,in_new_dirs,in_old_dirs,in_new,in_old,touched)

	
def path_patch(olderrors,modified,old,new,strict_old,strict_new,touched):
	return path_patch1(olderrors,modified,{**old,**strict_old},{**new,**strict_new},touched)

def path_back_patch(olderrors,modified,old,new,strict_old,strict_new,touched):
	return path_back_patch1(olderrors,modified,{**old,**strict_old},{**new,**strict_new},touched)

def hash_diff(oldroot_d,root_d):
	modified,old,new,strict_old,strict_new,touched = path_diff(oldroot_d,root_d)
	assert set(old)&set(strict_old) == set()
	assert set(new)&set(strict_new) == set()
	moved,old_dirs,new_dirs,old,new = hash_diff1(old,new)
	assert set(old)&set(strict_old) == set()
	assert set(new)&set(strict_new) == set()
	return (modified,moved,old_dirs,new_dirs,{**old,**strict_old},{**new,**strict_new},touched)

# # --------------------- DUMP, LOAD --------------------
# In[21]:


def path_patch_dump(in_modified,in_old,in_new,in_strict_old,in_strict_new,in_touched):
	modified = {}
	for path,v in in_modified.items():
		modified['/'.join(path)] = (nested_join(v[0]),nested_join(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched['/'.join(path)] = (nested_join(v[0]),nested_join(v[1]))
	old = {}
	for path,v in in_old.items():
		old['/'.join(path)] = nested_join(v)
	new = {}
	for path,v in in_new.items():
		new['/'.join(path)] = nested_join(v)
	strict_old = {}
	for path,v in in_strict_old.items():
		strict_old['/'.join(path)] = nested_join(v)
	strict_new = {}
	for path,v in in_strict_new.items():
		strict_new['/'.join(path)] = nested_join(v)
	return {
		'modified':modified,
		'old':old,
		'new':new,
		'strict_old':strict_old,
		'strict_new':strict_new,
		'touched':touched,
	}

def path_patch_load(obj):
	in_modified   = obj["modified"]   if 'modified' in obj else {}
	in_old        = obj["old"]        if 'old' in obj else {}
	in_new        = obj["new"]        if 'new' in obj else {}
	in_strict_old = obj["strict_old"] if 'strict_old' in obj else {}
	in_strict_new = obj["strict_new"] if 'strict_new' in obj else {}
	in_touched    = obj["touched"]    if 'touched' in obj else {}

	modified = {}
	for path,v in in_modified.items():
		modified[tuple(path.split('/'))] = (nested_split(v[0]),nested_split(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched[tuple(path.split('/'))] = (nested_split(v[0]),nested_split(v[1]))

	old = {}
	for path,v in in_old.items():
		old[tuple(path.split('/'))] = nested_split(v)
	new = {}
	for path,v in in_new.items():
		new[tuple(path.split('/'))] = nested_split(v)
	strict_old = {}
	for path,v in in_strict_old.items():
		strict_old[tuple(path.split('/'))] = nested_split(v)
	strict_new = {}
	for path,v in in_strict_new.items():
		strict_new[tuple(path.split('/'))] = nested_split(v)
	return (modified,old,new,strict_old,strict_new,touched)

def hash_patch_dump(in_modified,in_moved,in_old_dirs,in_new_dirs,in_old,in_new,in_touched):
	modified = {}
	for path,v in in_modified.items():
		modified['/'.join(path)] = (nested_join(v[0]),nested_join(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched['/'.join(path)] = (nested_join(v[0]),nested_join(v[1]))
	moved = []
	for from_p,to_p,from_obj,to_obj in in_moved:
		moved.append(('/'.join(from_p),'/'.join(to_p),nested_join(from_obj),nested_join(to_obj)))
	old_dirs = {}
	for path,v in in_old_dirs.items():
		old_dirs['/'.join(path)] = nested_join(v)
	new_dirs = {}
	for path,v in in_new_dirs.items():
		new_dirs['/'.join(path)] = nested_join(v)
	old = {}
	for path,v in in_old.items():
		old['/'.join(path)] = nested_join(v)
	new = {}
	for path,v in in_new.items():
		new['/'.join(path)] = nested_join(v)
	return {
		'modified':modified,
		'moved':moved,
		'old_dirs':old_dirs,
		'new_dirs':new_dirs,
		'old':old,
		'new':new,
		'touched':touched,
	}

def hash_patch_load(obj):
	in_modified = obj["modified"] if 'modified' in obj else {}
	in_moved    = obj["moved"]    if 'moved' in obj else []
	in_old_dirs = obj["old_dirs"] if 'old_dirs' in obj else {}
	in_new_dirs = obj["new_dirs"] if 'new_dirs' in obj else {}
	in_old      = obj["old"]      if 'old' in obj else {}
	in_new      = obj["new"]      if 'new' in obj else {}
	in_touched  = obj["touched"]  if 'touched' in obj else {}

	modified = {}
	for path,v in in_modified.items():
		modified[tuple(path.split('/'))] = (nested_split(v[0]),nested_split(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched[tuple(path.split('/'))] = (nested_split(v[0]),nested_split(v[1]))
	moved = []
	for from_p,to_p,from_obj,to_obj in in_moved:
		moved.append((tuple(from_p.split('/')),tuple(to_p.split('/')),nested_split(from_obj),nested_split(to_obj)))
	old_dirs = {}
	for path,v in in_old_dirs.items():
		old_dirs[tuple(path.split('/'))] = nested_split(v)
	new_dirs = {}
	for path,v in in_new_dirs.items():
		new_dirs[tuple(path.split('/'))] = nested_split(v)
	old = {}
	for path,v in in_old.items():
		old[tuple(path.split('/'))] = nested_split(v)
	new = {}
	for path,v in in_new.items():
		new[tuple(path.split('/'))] = nested_split(v)
	return (modified,moved,old_dirs,new_dirs,old,new,touched)
	
def action2tree(actions):
	tree = {}
	for action,pathlist in actions.items():
		for path,data in pathlist.items():
			if path=='':
				path = (action,)
			else:
				path = tuple('/'+x for x in path.split('/'))+(action,)
			set_subtree(tree,path,data)
	return tree
	
def tree2action(tree,ignore={'comment','statistics'}):
	actions={}
	for path,data in tree_iterator(tree,lambda x: not x.startswith('/')):
		if path[-1] in ignore:
			continue
		assert not path[-1].startswith('/')
		if path[-1] not in actions:
			actions[path[-1]]={}
		actions[path[-1]][''.join(path[:-1])[1:]] = data
	return actions
	
def moved2pathlist(moved):
	pathlist = {}
	for m in moved:
		p0 = m[0].split('/')
		p1 = m[1].split('/')
		i=0
		for i in range(min(len(p0),len(p1))):
			if p0[i]!=p1[i]:
				break
		M=[ '/'.join(p0[i:]),
		 '/'.join(p1[i:]), m[2], m[3] ]
		path = '/'.join(p0[:i])
		if path not in pathlist:
			pathlist[path] = []
		pathlist[path].append(M)
	return pathlist
	
def pathlist2moved(pathlist):
	moved = []
	for path,data in pathlist.items():
		for m in data:
			if len(m)!=4: 
				print(path,m)
			if path == '':
				moved.append([m[0],m[1], m[2], m[3]])
			else:
				moved.append([path+'/'+m[0], path+'/'+m[1], m[2], m[3]])
	return moved
	
def statistics(root,limit=1_000_000_000):
	def add_stat(o1,o2):
		o3 = {}
		for k in o1:
			t1 = [0 if x=='None' or x=='-None' else int(x) for x in o1[k].split(' ')]
			t2 = [0 if x=='None' or x=='-None' else int(x) for x in o2[k].split(' ')]
			t3=[]
			for i in range(len(t1)):
				t3.append(str(t1[i]+t2[i]))
			o3[k] = ' '.join(t3)
		return o3
	assert type(root)==dict
	st = {'new':'0 0','old':'0 0','modified':'0 0 0','moved':'0','touched':'0'}
	#print(root)
	for key in root:
		#print(key)
		st2 = {'new':'0 0','old':'0 0','modified':'0 0 0','moved':'0','touched':'0'}
		if key.startswith('/'):
			st2 = statistics(root[key],limit)
		elif key=='new':
			n=0; s=0
			#print(key,root[key])
			if type(root[key])==dict:
				for p,v in tree_iterator(root[key]):
					n+=1
					x = v.split(' ')[1]
					s+=0 if x=='None' or x=='-None' else int(x)
			else:
				n=1; s=int(root[key].split(' ')[1])
			st2 = {'new':str(n)+' '+str(s),
					   'old':'0 0','modified':'0 0 0','moved':'0','touched':'0'}
		elif key=='old':
			n=0; s=0
			if type(root[key])==dict:
				for p,v in tree_iterator(root[key]):
					n+=1
					s-=int(v.split(' ')[1])
			else:
				n=1; s=-int(root[key].split(' ')[1])
			st2 = {'old':str(n)+' '+str(s),
					   'new':'0 0','modified':'0 0 0','moved':'0','touched':'0'}
		elif key=='modified':
			so='-'+root[key][0].split(' ')[1]
			sn=    root[key][1].split(' ')[1]
			st2 = {'old':'0 0','new':'0 0','modified':'1 '+sn+' '+so,'moved':'0','touched':'0'}
		elif key=='touched':
			st2 = {'old':'0 0','new':'0 0','touched':'1','moved':'0','modified':'0 0 0'}
		elif key=='moved':
			n=0
			for v in root[key]:
				n+=1
			st2 = {'old':'0 0',
					   'new':'0 0','modified':'0 0 0','moved':str(n),'touched':'0'}
		st = add_stat(st,st2)
	def prettify(o1):
		o3 = {}
		yes = False
		for k in o1:
			t1 = [int(x) for x in o1[k].split(' ')]
			t3=[str(t1[0])]
			for i in range(1,len(t1)):
				x=t1[i]
				#print(x,limit)
				if abs(x)>limit:
					yes=True
				B = abs(x)%1024
				K = abs(x)//1024%1024
				M = abs(x)//1024//1024%1024
				G = abs(x)//1024//1024//1024
				if G>10:
					t3.append(str(G)+'Gb')
				elif G>0:
					t3.append(str(G)+'Gb'+str(M)+'Mb')
				elif M>10:
					t3.append(str(M)+'Mb')
				elif M>0:
					t3.append(str(M)+'Mb'+str(K)+'kb')
				elif K>10:
					t3.append(str(K)+'kb')
				elif K>0:
					t3.append(str(K)+'kb'+str(B)+'b')
				else:
					t3.append(str(B)+'b')
				if x<0:
					t3[-1]='-'+t3[-1]
			o3[k] = ' '.join(t3)
		return o3 if yes else None
	wst = prettify(st)
	if wst:
		root['statistics']= wst
	return st
	
	path_patch_compress
	path_patch_uncompress
	hash_patch_compress
	hash_patch_uncompress
	
def path_patch_compress(in_modified,in_old,in_new,in_strict_old,in_strict_new,in_touched):
	hp = path_patch_dump(in_modified,in_old,in_new,in_strict_old,in_strict_new,in_touched)
	#hp['moved'] = moved2pathlist(hp['moved'])
	hp = action2tree(hp)
	hp = nested_join(hp,'',lambda x: not x.startswith('/'),lambda x:x)
	statistics(hp,300_000_000)
	return hp

def path_patch_uncompress(obj):
	obj = nested_split(obj,'/',False,lambda x: not x.startswith('/'),lambda x:x)
	obj = tree2action(obj)
	#obj['moved'] = pathlist2moved(obj['moved'])
	return path_patch_load(obj)

def hash_patch_compress(in_modified,in_moved,in_old_dirs,in_new_dirs,in_old,in_new,in_touched):
	hp = hash_patch_dump(in_modified,in_moved,in_old_dirs,in_new_dirs,in_old,in_new,in_touched)
	hp['moved'] = moved2pathlist(hp['moved'])
	hp = action2tree(hp)
	hp = nested_join(hp,'',lambda x: not x.startswith('/'),lambda x:x)
	statistics(hp,300_000_000)
	return hp

def hash_patch_uncompress(obj):
	obj = nested_split(obj,'/',False,lambda x: not x.startswith('/'),lambda x:x)
	obj = tree2action(obj)
	
	#if 'modified' not in obj: obj["modified"] = {}
	if 'moved'    not in obj: obj["moved"]    = {}
	#if 'old_dirs' not in obj: obj["old_dirs"] = {}
	#if 'new_dirs' not in obj: obj["new_dirs"] = {}
	#if 'old'      not in obj: obj["old"]      = {}
	#if 'new'      not in obj: obj["new"]      = {}
	#if 'touched'  not in obj: obj["touched"]  = {}

	obj['moved'] = pathlist2moved(obj['moved'])
	return hash_patch_load(obj)

def load_snapshot(path):
	tmp = strip_json_scomments(myjson_load(path))
	return nested_split(tmp['errors']),nested_split(tmp['root'])

def dump_snapshot(errors,root,path):
	myjson_dump({
		'errors':nested_join(errors),
		'root':nested_join(root)
	},path)

# # --------------------- PATCH CHEIN --------------------

def check_list(path='.',start = None):
	ls = os.listdir(path)
	ols = find_date_file('patch ','.json',ls)
	r = {}
	l = {}
	for s in ols:
		f,t = s.split(' to ')
		r[f]=t
		l[t]=f
	if not start:
		start = next(iter(r))
	lst = [start]
	while lst[0] in l:
		cur = lst[0]
		lst.insert(0,l[cur])
		del r[l[cur]]
		del l[cur]
	while lst[-1] in r:
		cur = lst[-1]
		lst.append(r[cur])
		del l[r[cur]]
		del r[cur]
	#assert len(l)==len(r)
	if len(r)>0:
		print('осталось',len(r),'переходов')
	return lst
	
def patch_chain(lst,frm,to,in_snapshot):
	if type(frm)!=int:
		frm=lst.index(frm)
	assert frm>=0 and frm<len(lst)
	if type(to)!=int:
		to=lst.index(to)
	assert to>=0 and to<len(lst)
	errors = in_snapshot['errors']
	root = in_snapshot['root']
	print(frm,to)
	if frm<to: # to right
		for i in range(frm,to):
			path = 'patch '+lst[i]+' to '+lst[i+1]+'.json'
			print(path)
			patch = myjson_load(path)
			
			#e_modified_d,e_old_d,e_new_d,e_strict_old_d,e_strict_new_d,e_touched_d = \
			#    path_patch_uncompress(patch['errors'])
			errors = path_patch(errors,*path_patch_uncompress(patch['errors']))
			
			#modified_d,moved_d,old_dirs_d,new_dirs_d,old_d,new_d,touched_d = \
			#    hash_patch_uncompress(patch['root'])
			root = hash_patch(root,*hash_patch_uncompress(patch['root']))

	elif frm>to: # to left
		for i in range(frm,to,-1):
			path = 'patch '+lst[i-1]+' to '+lst[i]+'.json'
			print('back',path)
			patch = myjson_load(path)
			
			#e_modified_d,e_old_d,e_new_d,e_strict_old_d,e_strict_new_d,e_touched_d = \
			#    path_patch_uncompress(patch['errors'])
			errors = path_back_patch(errors,*path_patch_uncompress(patch['errors']))
			
			#modified_d,moved_d,old_dirs_d,new_dirs_d,old_d,new_d,touched_d = \
			#    hash_patch_uncompress(patch['root'])
			root = hash_back_patch(root,*hash_patch_uncompress(patch['root']))
	return {'errors':errors,'root':root}
	
def diff(old_snap,new_snap):
	return {
		'errors':path_patch_compress(*path_diff(old_snap['errors'],new_snap['errors'])),
		'root':hash_patch_compress(*hash_diff(old_snap['root'],new_snap['root']))
	}
