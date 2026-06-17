import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import pickle

import data

enter = '\n'
ax_data_cutoff = 10
row_lim = 4
ax_size = [1,1]                                  #x , y length of axes
ax_space = [0.2 , 0.2]
common_dpi = 120
sketch_dpi = 180
gc_c_ene = 6                                  #charcteristic energy
sig_c_ene = 5

tag_list = [['GF','inpx','sig']]



class album:                                    # 3-level structure , album - page - figure
    def __init__(self):
        self.comment = ''
        self.album = []

    def __str__(self):
        r = ''
        for p in range(0,len(self.album)):
            r = r + 'num : ' + str(p) + ' key_tag :'+ self.album[p].__str__()  + enter

        return r

    def show(self):
        r = ''
        for f in range(0,len(self.fig_list)): 
            r = r + 'fig : ' + str(f) + ' ' +  self.fig_list[f].__str__() + enter
        print(r)

    def __del__(self):
        del self.album
        del self.comment

    def init(self,type,tag_list,source_list):
        if type in init_list:
            init_list[type](self , tag_list,source_list)
        else:
            print('no match init()')
    
    def page_cl_dt(self,source_list,key_tag):
        self.album.append(page())
        data.add_data_my(self.album[-1].mission.data , source_list , key_tag)
        self.album[-1].key_tag = key_tag

    def create_page(self,source_list,key_tag):
        self.page_cl_dt(source_list,key_tag)
        self.album[-1].init()
   
    

    def save_pkl(self,dir):
        with open(dir, 'wb') as file:
            pickle.dump(self, file)
        
        
        







class page:
    def __init__(self):
        self.mission = data.mission() 
        self.ax_data = []
        self.m_ax = []
        self.fig_list = []
        self.key_tag = ''
        self.sketch = plt.figure(dpi = sketch_dpi)
        self.modifier_list = modifier_list
        

    def __str__(self):
        r = self.key_tag + ' fig_num : ' + str(len(self.fig_list))
        return r
    

    def add_data(self,input):
        data.add_data(self.mission.data,input)

    def init(self): 
        if len(self.mission.data) == 0 :
            print('data id void')
            return
        
        self.group_k()
        self.draw_sk()
        self.draw()
        

    def update(self):
        
        del self.fig_list 
        del self.sketch
        del self.ax_data
        self.fig_list = []
        self.sketch = plt.figure()
        self.ax_data = []

        self.group_k()
        self.draw_sk()
        self.draw()
        

    def get_f(self,id):               #get_figure 
        return self.fig_list[id]

    #def show_f(self,id):
    #    return self.fig_list[id].figure

    def group_k(self):            #group by key_tag
        for d in self.mission.data:
            flag = 0
            for a in self.ax_data:
                if a[0].key_tag == d.key_tag:
                    a.append(d)
                    flag = 1
                    break
            if flag == 0:
                self.ax_data.append([d])
    
    def add_sk_ax(self):
        ax_id = len(self.sketch.get_axes())
        y = ax_id // row_lim 
        x = ax_id % row_lim
        
        x_pos = (x - 1) * (ax_size[0] + ax_space[0])
        y_pos = (y - 1) * (ax_size[1] + ax_space[1])

        self.sketch.add_axes([x_pos , y_pos] + ax_size)
    
    def add_fig(self):
        self.fig_list.append(plt.figure(dpi= common_dpi ))
        self.fig_list[-1].add_axes([0 , 0] + ax_size)

    def draw(self):
        for ad in self.ax_data:
            if len(ad) == 1:
                plot_f_sg(self,ad[0],self.modifier_list)

            else:
                plot_f_list(self,ad,self.modifier_list)

    def draw_sk(self):
        for ad in self.ax_data:
            if len(ad) == 1:
                plot_ax_sg(self,ad[0],self.modifier_list)

            else:
                plot_ax_list(self,ad,self.modifier_list)
        
        self.sketch.suptitle(self.key_tag , fontsize=25)

        

    def __del__(self):
        del self.mission
        del self.ax_data 
        del self.fig_list 
        del self.sketch



    
def plot_f_sg(pg,dat : data.data , mdf_list = {}):       #single data
    pg.add_fig()
    mdf = default_ax_modifier
    type = dat.type
    if type in mdf_list:
        mdf = mdf_list[type]

    for i in range(1,len(dat.data)):
        pg.fig_list[-1].axes[0].plot(dat.data[0,:],dat.data[i,:],label = dat.label[i])
    
    pg.fig_list[-1].axes[0].set_xlabel(dat.label[0])
    pg.fig_list[-1].axes[0].set_ylabel(dat.key_tag)
    pg.fig_list[-1].axes[0].set_title(dat.name)
    pg.fig_list[-1].axes[0].legend()
    pg.fig_list[-1].axes[0].grid()
    mdf(pg.fig_list[-1].axes[0],dat)
    




    

def plot_f_list(pg,dat, mdf_list = {}):    # dat is a list of data
    l_tmp = []
    for d in dat:
        l_tmp.append(len(d.data))
    mdf = default_ax_modifier
    type = dat[0].type
    if type in mdf_list:
        mdf = mdf_list[type]
    length = min(l_tmp)
    for i in range(1,length):
        pg.add_fig()

    for i in range(1,length):
        for j in range(0,min(len(dat),ax_data_cutoff)):
            pg.fig_list[i-length].axes[0].plot(dat[j].data[0,:],dat[j].data[i,:] , label = dat[j].name)

    for i in range(1,length):
            pg.fig_list[i-length].axes[0].set_xlabel(dat[0].label[0])
            pg.fig_list[i-length].axes[0].set_ylabel(dat[0].key_tag)
            pg.fig_list[i-length].axes[0].set_title(dat[0].label[i])
            pg.fig_list[i-length].axes[0].legend()
            pg.fig_list[i-length].axes[0].grid()
            mdf(pg.fig_list[i-length].axes[0],dat[0])

    

def plot_ax_sg(pg,dat, mdf_list = {}):       #single data
    pg.add_sk_ax()
    mdf = default_ax_modifier
    type = dat.type
    if type in mdf_list:
        mdf = mdf_list[type]
    for i in range(1,len(dat.data)):
        pg.sketch.axes[-1].plot(dat.data[0,:],dat.data[i,:],label = dat.label[i])
    
    pg.sketch.axes[-1].set_xlabel(dat.label[0])
    pg.sketch.axes[-1].set_ylabel(dat.key_tag)
    pg.sketch.axes[-1].set_title(dat.name)
    pg.sketch.axes[-1].legend()
    pg.sketch.axes[-1].grid()
    mdf(pg.sketch.axes[-1],dat)
    




    

def plot_ax_list(pg,dat, mdf_list = {}):    # dat is a list of data
    l_tmp = []
    for d in dat:
        l_tmp.append(len(d.data))
   
    length = min(l_tmp)
    mdf = default_ax_modifier
    type = dat[0].type
    if type in mdf_list:
        mdf = mdf_list[type]
    for i in range(1,length):
        pg.add_sk_ax()

    for i in range(1,length):
        for j in range(0,min(len(dat),ax_data_cutoff)):
            pg.sketch.axes[i-length].plot(dat[j].data[0,:],dat[j].data[i,:] , label = dat[j].name)

    for i in range(1,length):
            pg.sketch.axes[i-length].set_xlabel(dat[0].label[0])
            pg.sketch.axes[i-length].set_ylabel(dat[0].key_tag)
            pg.sketch.axes[i-length].set_title(dat[0].label[i])
            pg.sketch.axes[i-length].legend()
            pg.sketch.axes[i-length].grid()
            mdf(pg.sketch.axes[i-length],dat[0])
            


def default_ax_modifier(in_ax,dat):   #work on axes
    pass

def edmft_ax_modifier(in_ax : matplotlib.axes._axes.Axes ,dat : data.data):   #work on axes
    if dat.key_tag == 'gc1':
        if dat.data[0][0] < 0:
            in_ax.set_xlim([-gc_c_ene,gc_c_ene])

        else:
            in_ax.set_xlim([0,gc_c_ene])
    if dat.key_tag == 'sig':
        if dat.data[0][0] < 0:
            in_ax.set_xlim([-sig_c_ene,sig_c_ene])

        else:
            in_ax.set_xlim([0,sig_c_ene])
    if dat.key_tag == 'dlt1':
        if dat.data[0][0] < 0:
            in_ax.set_xlim([-gc_c_ene,gc_c_ene])

        else:
            in_ax.set_xlim([0,gc_c_ene])
    if dat.key_tag == 'cdos':
        if dat.data[0][0] < 0:
            in_ax.set_xlim([-gc_c_ene,gc_c_ene])

        else:
            in_ax.set_xlim([0,gc_c_ene])

    

modifier_list = {'edmft' : edmft_ax_modifier}

def edmft_init(alb : album ,tag_list, source_list):
    
    for t in tag_list:
        alb.create_page(source_list , t)


init_list = {'edmft' : edmft_init}

def load_alb(dir):
    with open(dir, 'rb') as file:
        tmp = pickle.load(file)
    
    return tmp