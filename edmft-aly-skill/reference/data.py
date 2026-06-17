import os 
import numpy as np
import copy
import pickle
enter = '\n'
div_list=['\\','.','/']  
#edmft / vasp /
target = [['sig','cdos','gc1','dlt1'] , 
          ['TDOS','PDOS']]

#edmft-4f / 
label = [ {'sig' : ['w','5/2-r','5/2-i','7/2-r','7/2-i']  , 'cdos':['w','total','f'] ,'gc1' : ['w','5/2-r','5/2-i','7/2-r','7/2-i']
           , 'dlt1' : ['w','5/2-r','5/2-i','7/2-r','7/2-i']}]

filter_list = ['inp1','inp2','inp3','out','bd','maxent']

#the root dir level
class datacol:
    def __init__(self):
        self.prefix = ''
        self.mission_list = []

    def __str__(self):
        if len(self.mission_list) == 0: 
            return 'data collection empty'
        else:
            r=''
            for i in range(0,len(self.mission_list),1):
                r = r + str(i) + ' : '+ self.mission_list[i].__str__() 
            return r 
    
    def set(self,pwd):
        self.prefix = pwd

    def __del__(self):
        del self.mission_list

    def save_pkl(self,dir):
        with open(dir, 'wb') as file:
            pickle.dump(self, file)

# one of the calculation , such as one of the temperature or pressure point 
class mission:
    def __init__(self):
        self.dir = ''
        self.title = ''
        self.comment = ''
        self.target_list = []   #files should be included
        self.label_list = {}
        self.type = ''

        self.data = []
        
    def __str__(self):
        r = self.title + ' ' + self.comment + ' |size : ' + str(len(self.data)) 
        return r
    
    def show(self):
        print('data num = ' + str(len(self.data)))
        r=' '
        for i in range(0,len(self.data),1):
            r = r + str(i) + ' : '+ self.data[i].__str__() + enter
        print(r)
               
    def set(self,input,target,label_list,type = ''):
        self.dir = input[0]
        self.title = input[1]
        self.type = type

        if len(input) == 3:
           self.comment = input[2]

        self.target_list = target
        self.label_list = label_list

    def add(self,input):       #input should be 3-str-list
        self.data.append(data())
        self.data[-1].get(input)


    def pull(self):
        file_list = []
        root = self.dir
        tmp = '' 
        mdf = default_modifier
        if self.type in modifier_list:
            mdf = modifier_list[self.type]

        for i in os.walk(root):
            for j in i[2]:
                tmp = i[0] + '/' + j
                file_list.append(tmp)



        for f in file_list:
            tmp = f.replace(root,'')
            for d in div_list:
                tmp = tmp.replace(d,'-')
            tmp_sp=tmp.split('-')
            for t in self.target_list:

                if t in tmp_sp:
                    flag = 0
                    for fl in filter_list:
                        if fl in tmp_sp:
                            flag = 1
                            break
                    if flag == 1:
                        break
                    
                    self.data.append(data())
                    if t in self.label_list:
                        label = self.label_list[t]
                    else:
                        label = []
                    self.data[-1].get([self.title + '-' + tmp,t,f,self.type],label)
                    mdf(self.data[-1])
                    break    


    def __del__(self):
        del self.target_list
        del self.label_list
        del self.data

    


#one output file in a mission
class data:                                 
    def __init__(self):
        
        self.data = np.array([])            #cols from file
        self.label = []                     #cols name
        self.key_tag = ''                   #extension of the file
        self.tag= []
        self.name = ''                      #name of the file
        self.dir = ''
        self.c_num = -1                     # Characteristic number
        self.type = ''
         
  
    def __str__(self):
        r = self.name + '  ' + self.key_tag + ' num : ' +  str(len(self.data) - 1)
        return r
    
    def get(self,input,label):   #input should be 3-str-list
        self.name = input[0]
        self.key_tag = input[1]
        self.dir = input[2]
        self.type = input[3]       
        self.tag = self.name.split('-')

        for t in self.tag :
            if t.isnumeric() :
                self.c_num = int(t)
                break
        #print(input[2])
        tmp = np.loadtxt(input[2], skiprows = 1)
        self.data = np.transpose(tmp)  

        if len(label) != len(self.data):
            ld = []
            for i in range(0,len(self.data)):
                ld.append('c'+str(i))

            self.label = ld
        else:
            self.label = copy.deepcopy(label)

    def d_copy(self,input):
        self.data = copy.deepcopy(input.data)            #cols from file
        self.label = copy.deepcopy(input.label)                    #cols name
        self.key_tag = copy.deepcopy(input.key_tag)                   #extension of the file
        self.tag= copy.deepcopy(input.tag)
        self.name = copy.deepcopy(input.name)                      #name of the file
        self.dir = copy.deepcopy(input.dir)
        self.c_num = copy.deepcopy(input.c_num)
        self.type = copy.deepcopy(input.type)

    def __del__(self):
        del self.data
        del self.label
        del self.tag
        
        
#subroutines
def rm_data_s(in_list , rm_tag : str):      
    
      for i in range(len(in_list)-1,-1,-1):
            for t in in_list[i].tag:
                if t == rm_tag :
                    in_list.pop(i)
                    break

def rm_data_n(in_list ):      
    
      for i in range(len(in_list)-1,-1,-1):
            if in_list[i].c_num > -1:
                in_list.pop(i)

def rs_data_s(in_list , rs_tag : str):      
      flag = 0
      for i in range(len(in_list)-1,-1,-1):
            flag = 0
            for t in in_list[i].tag:
                if t == rs_tag :
                    flag = 1
                    break
            if(flag == 0):
                in_list.pop(i)

def rm_data(in_list , rm_tag : list):      
      for r in rm_tag:
           rm_data_s(in_list,r)
                   
def sig_filter(in_list,end):
    t = range(end - 9, end)
    for i in range(len(in_list)-1,-1,-1):
        if in_list[i].key_tag == 'sig':
            if in_list[i].c_num > -1:
                if in_list[i].c_num in t:
                  pass
                else:    
                    in_list.pop(i)
            else:
                if 'inpx' in in_list[i].tag:
                    pass
                else:    
                    in_list.pop(i)
      
def add_data_s(in_list,source_list , add_tag : str):      #subroutine
    
      for s in source_list:
            for t in s.tag:
                if t == add_tag :
                    in_list.append(data())
                    in_list[-1].d_copy(s)
                    break

def add_data_my(in_list,source_list , add_tag : str):      #subroutine
    for m in source_list:
        add_data_s(in_list,m.data,add_tag)

def get_data(in_list ,source_list, add_tag : list):      # & of add_tag
      for a in add_tag:
           add_data_s(in_list,source_list,a)

def add_data(in_list,source_list):  
    for i in source_list:
        in_list.append(data())
        in_list[-1].d_copy(i)   


def default_modifier(dat):
    pass

def edmft_modifier(dat):
    if dat.key_tag == 'sig':
        tmp = ''.join(reversed(dat.name))
        tmp = tmp.replace('1-','',1)
        dat.name = ''.join(reversed(tmp))
        if '1' in dat.tag:
            dat.tag.remove('1')
    elif dat.key_tag == 'gc1':
        if dat.data[0][0] < 0:
            for i in range(2,len(dat.data),2):
                dat.data[i] = dat.data[i] * -1
                dat.label[i] = dat.label[i] + '(nag)'
    elif dat.key_tag == 'dlt1':
        if dat.data[0][0] < 0:
            for i in range(2,len(dat.data),2):
                dat.data[i] = dat.data[i] * -1
                dat.label[i] = dat.label[i] + '(nag)'
            
                



modifier_list = {'edmft' : edmft_modifier}

def load_dcl(dir):
    with open(dir, 'rb') as file:
        tmp = pickle.load(file)
    
    return tmp