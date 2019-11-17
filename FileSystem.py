#!/usr/bin/env python
# coding: utf-8

# # сканирование, и подсчет хешей

# проверка на симлинки
# стандартная проверка в windows junction-ы не считает симлинками

__all__ = [
# # ------------------- UTILS ----------------
	# seq - tuple or list
	# path - sequence of str
	"my_path_join_a", #(*seq)->str
	"my_path_join_l", #(seq)->str
	"tree_iterator",  #(tree) yield (path,obj)
	"get_subtree",    #(root,path) -> obj
	"make_subtree",   #(root,path) -> obj
	"is_subpath",     #(long_path,short_path)->bool
# # ------------------- SCAN ------------------------
	"scan",           #(rootpath,exceptions=set())->file_tree
	"calc_hashes",    #(->root,old_root,prefix)
# # ------------------- DIFF --------------
	"first_diff",     #(old_root,root) -> True or (path,(old,new))
	"path_diff",      #(old_root,root) -> (modified,old,new,strict_old,strict_new,touched)
	"hash_diff",      #(old,new)       -> (moved,old_dirs,new_dirs,old,new)
# # ---------------------- PATCH, SYNC -------------------------
	"path_patch",     #(old_root,modified,old,new, touched = {}) -> new_root
	"hash_patch",     #(old_root,modified,moved,old_dirs,new_dirs,old,new, touched={}) -> new_root
	# path_patch_back
	"hash_back_patch",#(new_root,modified,moved,old_dirs,new_dirs,old,new, touched={}) -> old_root
	# path_sync
	# hash_sync
# # --------------------- DUMP, LOAD --------------------
	"myjson_load",    #(path)->obj
	"myjson_dump",    #(obj,path)
	"myjson_dumps",   #(obj)->str
	"clear_json_comment",#(obj)->obj
	#сжатие путей и файлов в одну строку
	"tree_dump",      #(root)->root
	"tree_load",      #(root)->root
	# + сортировка по путям (комментами)
	"path_patch_dump",#(modified      ,old,new,strict_old,strict_new,touched)->obj
	"hash_patch_dump",#(modified,moved,old_dirs,new_dirs,old,new    ,touched)->obj
	#"path_patch_load",#obj->(modified      ,old,new,strict_old,strict_new,touched)
	"hash_patch_load",#obj->(modified,moved,old_dirs,new_dirs,old,new    ,touched)
]


DT = 1 # 1 second between timestamps

# # ------------------- UTILS ----------------
# In[3]:


# прогресс-бар числом - для случаев while и т.п.
from ipywidgets import HTML
from IPython.display import display
from time import sleep
#label = HTML()
#display(label)
#for x in range(10):
#	label.value = str(x)
#	sleep(0.1)


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


# In[6]:


def tree_iterator(tree):
	"""проходится по всему дереву
	на каждом узле(листе) возвращает пару (путь, значение)
	где путь - список имен, по которым надо добираться по дереву до значения"""
	if type(tree)!=dict:
		yield (),tree
		return
	for k,v in tree.items():
		if type(v)==dict:
			for path,v2 in tree_iterator(v):
				#path.insert(0,k)
				yield (k,)+path,v2
		else:
			yield (k,),v
#r = {'a':1,'b':{'c':2,'d':3}}
#for x in tree_iterator(r):
#	print(x)


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
def make_subtree(root,path):
	"""берет корень и путь, проходит по пути и создает его, если его нет"""
	if len(path)==0: return root
	else: 
		if path[0] not in root: root[path[0]]={}
		return make_subtree(root[path[0]],path[1:])
def is_subpath(subpath,path):
	"""сначала длинный, потом короткий"""
	if len(subpath)<len(path):
		return False
	for i in range(len(path)):
		if subpath[i]!=path[i]:
			return False
	return True


# # ------------------- SCAN ------------------------
# In[2]:


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

#is_winlink(r'D:\Users\feelus\Local Settings')


# In[5]:


def scan(rootpath,exceptions=set()):
	total_size = 0
	ts_printed = 0

	label = HTML()
	display(label)

	def scan1(curpath):
		nonlocal total_size
		nonlocal ts_printed
		if curpath in exceptions:
			return {}
		curroot = {}
		#print(curpath)
		try:
			with os.scandir(curpath) as it:
				for entry in it:
					if entry.name!='.' and entry.name!='..':
						if entry.is_dir(follow_symlinks=False):
							curroot[entry.name] = scan1(entry.path)
						elif entry.is_file(follow_symlinks=False):
							st = entry.stat(follow_symlinks=False)
							curroot[entry.name] = [st.st_mtime,st.st_size]
							total_size+=st.st_size
						elif not entry.is_symlink() and not is_winlink(entry.path):
							print('unknown object:',entry.path)
		except OSError as e:
			print(curpath)
			print(e)
			print()
			return {}
		if ts_printed<int(total_size/1024/1024/1024):
			ts_printed = int(total_size/1024/1024/1024)
			label.value = str(ts_printed)+' GB scanned'
		return curroot
	tmp = scan1(rootpath)
	label.value = str(ts_printed)+' GB scanned - completed'
	return tmp


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


def calc_hashes(root,old_root,prefix):
	total_size = 0
	ts_printed = 0
	label = HTML()
	display(label)

	def calc_hashes1(root,old_root,path):
		nonlocal total_size
		nonlocal ts_printed
		
		for name in root.keys():
			if type(root[name])==dict: # directory
				if name in old_root and type(old_root[name])==dict:
					calc_hashes1(root[name],old_root[name],path+[name])
				else:
					calc_hashes1(root[name],{},path+[name])
			elif type(root[name])==list: # file
				assert len(root[name])>=2
				if name in old_root and type(old_root[name])==list and	\
				  len(old_root[name])>=3 and root[name][1]==old_root[name][1] and \
				  abs(root[name][0] - old_root[name][0]) < DT : # 1 second between timestamps
					if len(root[name])==2:
						root[name].append(old_root[name][2])
					else:
						root[name][2] = old_root[name][2]
				else:
					p = my_path_join_a(prefix,*path,name)
					try:
						#print(p)
						os.stat(p)  # зависает при чтении некоторых файлов
									# stat от этих файлов будет ошибкой
						if len(root[name])==2:
							root[name].append(md5(p))
						else:
							root[name][2] = md5(p)
					except OSError as e:
						if len(root[name])==2:
							root[name].append(None)
						print(p)
						print(e)
						print()
					
				if type(root[name][1])==int:
					total_size+=root[name][1]
				if ts_printed<int(total_size/1024/1024/1024):
					ts_printed = int(total_size/1024/1024/1024)
					label.value = str(ts_printed)+' GB calculated'
			else:
				raise BaseException(path)
				
	calc_hashes1(root,old_root,[])
	label.value = str(ts_printed)+' GB calculated - completed'


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
					raise BaseException(path_name)
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
						assert root[name][1]==old_root[name][1], path_name
						if abs(root[name][0]-old_root[name][0])>1:
							touched[path_name] = (old_root[name], root[name])
					elif root[name][2]==None and root[name][2]==old_root[name][2] and \
					  root[name][1]==old_root[name][1] and abs(root[name][0] - old_root[name][0]) < DT : # 1 second between timestamps
						# same files without hashes
						assert root[name][1]==old_root[name][1], path_name
						if abs(root[name][0]-old_root[name][0])>1:
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
					raise BaseException(path_name)
				else:
					# new file
					new[path_name] =	 root[name]
			else:
				raise BaseException(path_name)
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
					raise BaseException(path_name)
	diff1(root,old_root,())
	return (modified,old,new,strict_old,strict_new,touched)


# In[12]:


from copy import *

nest = 0

def print_lines(arg,caption=None):
	global nest
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
	

# In[13]:


def make_files(old):
	old_files = {}
	for p1,subtree in old.items():
		for p2,v in tree_iterator(subtree):
			if v[2] not in old_files:
				old_files[v[2]] = set()
			#print(p1,p2,tuple(p2))#,p1+tuple(p2))
			old_files[v[2]].add(p1+tuple(p2))
	return old_files


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
			if subtree[2] in new_files:
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
		else: raise BaseException(prefix_path)
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
			else: raise BaseException(path)
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
					assert dest_p[i+k] in tmp, BaseException((dest_p,i+k))
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


def hash_diff(old,new,verbose=1):
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
	old_files = make_files(old)
	new_files = make_files(new)

	#print_lines(old.keys(),'--- old.keys ---')
	#print_lines(new.keys(),'--- new.keys ---')
	#print_lines(old.items(),'--- old.items ---')
	#print_lines(new.items(),'--- new.items ---')
	#print_lines(old_files.items(),'--- old_files ---')
	#print_lines(new_files.items(),'--- new_files ---')

	# создаю moved, обходя и меняя old и new (несколько раз) (а также old_files и new_files)
	moved = make_moved(old_files,new_files,old,new,verbose)

	#print('-------')
	#print(myjson_dumps(tree_dump(new)))
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
		if h1 in new_files:
			flag = True
			#print(h1)
	if flag:
		raise BaseException(h1)

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
				raise BaseException((prefix,path,name,type(subtree[name])))

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
def path_patch(old_root,modified,old,new, touched = {}):
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
		assert parent[path[-1]] == obj
		del parent[path[-1]]
	for path,obj in new.items():
		parent = get_subtree(root,path[:-1])
		assert path[-1] not in parent
		parent[path[-1]] = deepcopy(obj)
	return root


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

	
# # --------------------- DUMP, LOAD --------------------
# In[10]:


import json, codecs

def myjson_load(hash_path):
	"""загружаем хэши, вычисляем хэши, сохраняем хэши"""
	try:
		with codecs.open(hash_path,'r', encoding='utf-8') as file:
			old_root = file.read()
			old_root = json.loads(old_root)
			print('readed',hash_path)
			print(old_root.keys())
	except BaseException as e:
		print(e)
		old_root = {}
	return old_root

def myjson_dumps(old_root):
	return json.dumps(old_root,indent='\t',ensure_ascii=False)

def myjson_dump(old_root,hash_path):
	try:
		print('start writing')
		with codecs.open(hash_path,'w', encoding='utf-8') as file:
			s = myjson_dumps(old_root)
			file.write(s)
			print('writed',hash_path)
	except BasicException as e:
		print('start writing with exception',e)
		with codecs.open(hash_path,'w', encoding='utf-8') as file:
			s = myjson_dumps(old_root)
			file.write(s)
			print('writed',hash_path)


def tree_merge(to_tree,from_tree):
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
		
def clear_json_comment(tree):
	if type(tree)==dict:
		new_tree = {}
		for name in tree:
			if name.startswith('//block'):
				for name2 in tree[name]:
					if name2!='//comment':
						if name2 in new_tree:
							tree_merge(new_tree[name2],tree[name][name2])
						else:
							new_tree[name2] = tree[name][name2]
			else:
				if name in new_tree:
					tree_merge(new_tree[name],tree[name])
				else:
					new_tree[name] = tree[name]
		return new_tree
	elif type(tree)==list:
		new_tree = []
		for obj in tree:
			new_tree.append(clear_json_comment(obj))
		return new_tree
	else:
		return tree
		
# In[18]:


def tree_dump(root):
	if type(root)==list:
		return str(root[0])+' '+str(root[1])+' '+str(root[2])
		# root[2] обычно строка, но иногда это None
	else:
		new_root = {}
		for name in root.keys():
			assert type(name)==str, name
			tmp_root = root
			name_path = name
			while type(tmp_root[name])==dict and len(tmp_root[name])==1:
				subname = next(iter(tmp_root[name]))
				assert type(subname)==str
				tmp_root = tmp_root[name]
				name_path+='/'+subname
				name = subname
			new_root[name_path] = tree_dump(tmp_root[name])
		return new_root


# In[19]:


#tree_dump({
#	'x':{
#		'y':[1,2,'3'],
#		#'z':[1,2,'3'],
#	}
#})


# In[35]:


def tree_load(root):
	if type(root)==str:
		# root[2] обычно строка, но иногда это None
		s = s.split(' ')
		s[0] = float(s[0])
		s[1] = int(s[1])
		if s[2]=='None': s[2]=None
		return s
	else:
		new_root = {}
		for name in root.keys():
			assert type(name)==str, name
			tmp = tree_load(root[name])
			tmp_name = name.split('/')
			while len(tmp_name)>1:
				tmp = {tmp_name[-1]:tmp}
				tmp_name = tmp_name[:-1]
			new_root[tmp_name] = tmp
		return new_root

# In[21]:


def path_patch_dump(in_modified,in_old,in_new,in_strict_old,in_strict_new,in_touched):
	modified = {}
	for path,v in in_modified.items():
		modified['/'.join(path)] = (tree_dump(v[0]),tree_dump(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched['/'.join(path)] = (tree_dump(v[0]),tree_dump(v[1]))
	old = {}
	for path,v in in_old.items():
		old['/'.join(path)] = tree_dump(v)
	new = {}
	for path,v in in_new.items():
		new['/'.join(path)] = tree_dump(v)
	strict_old = {}
	for path,v in in_strict_old.items():
		strict_old['/'.join(path)] = tree_dump(v)
	strict_new = {}
	for path,v in in_strict_new.items():
		strict_new['/'.join(path)] = tree_dump(v)
	return {
		'modified':modified,
		'old':old,
		'new':new,
		'strict_old':strict_old,
		'strict_new':strict_new,
		'touched':touched,
	}

def hash_patch_dump(in_modified,in_moved,in_old_dirs,in_new_dirs,in_old,in_new,in_touched):
	modified = {}
	for path,v in in_modified.items():
		modified['/'.join(path)] = (tree_dump(v[0]),tree_dump(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched['/'.join(path)] = (tree_dump(v[0]),tree_dump(v[1]))
	moved = []
	for from_p,to_p,from_obj,to_obj in in_moved:
		moved.append(('/'.join(from_p),'/'.join(to_p),tree_dump(from_obj),tree_dump(to_obj)))
	old_dirs = {}
	for path,v in in_old_dirs.items():
		old_dirs['/'.join(path)] = tree_dump(v)
	new_dirs = {}
	for path,v in in_new_dirs.items():
		new_dirs['/'.join(path)] = tree_dump(v)
	old = {}
	for path,v in in_old.items():
		old['/'.join(path)] = tree_dump(v)
	new = {}
	for path,v in in_new.items():
		new['/'.join(path)] = tree_dump(v)
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
	in_moved    = obj["moved"]    if 'moved' in obj else {}
	in_old_dirs = obj["old_dirs"] if 'old_dirs' in obj else {}
	in_new_dirs = obj["new_dirs"] if 'new_dirs' in obj else {}
	in_old      = obj["old"]      if 'old' in obj else {}
	in_new      = obj["new"]      if 'new' in obj else {}
	in_touched  = obj["touched"]  if 'touched' in obj else {}

	modified = {}
	for path,v in in_modified.items():
		modified[tuple(path.split('/'))] = (tree_load(v[0]),tree_load(v[1]))
	touched = {}
	for path,v in in_touched.items():
		touched[tuple(path.split('/'))] = (tree_load(v[0]),tree_load(v[1]))
	moved = []
	for from_p,to_p,from_obj,to_obj in in_moved:
		moved.append((tuple(from_p.split('/')),tuple(to_p.split('/')),tree_load(from_obj),tree_load(to_obj)))
	old_dirs = {}
	for path,v in in_old_dirs.items():
		old_dirs[tuple(path.split('/'))] = tree_load(v)
	new_dirs = {}
	for path,v in in_new_dirs.items():
		new_dirs[tuple(path.split('/'))] = tree_load(v)
	old = {}
	for path,v in in_old.items():
		old[tuple(path.split('/'))] = tree_load(v)
	new = {}
	for path,v in in_new.items():
		new[tuple(path.split('/'))] = tree_load(v)
	return (modified,moved,old_dirs,new_dirs,old,new,touched)
	
	
	