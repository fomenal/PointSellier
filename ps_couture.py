#!/usr/bin/env python
'''
Copyright (C) 2006 Jean-Francois Barraud, barraud@math.univ-lille1.fr

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
barraud@math.univ-lille1.fr

Quick description:
This script deforms an object (the pattern) along other paths (skeletons)...
The first selected object is the pattern
the last selected ones are the skeletons.

Imagine a straight horizontal line L in the middle of the bounding box of the pattern.
Consider the normal bundle of L: the collection of all the vertical lines meeting L.
Consider this as the initial state of the plane; in particular, think of the pattern
as painted on these lines.

Now move and bend L to make it fit a skeleton, and see what happens to the normals:
they move and rotate, deforming the pattern.
'''

# standard library
import copy
import math
import re
import random
import simplestyle
# local library
import inkex
import cubicsuperpath
import bezmisc
import pathmodifier
import simpletransform

inkex.localize()

def offset(pathcomp,dx,dy):
    for ctl in pathcomp:
        for pt in ctl:
            pt[0]+=dx
            pt[1]+=dy
                            
def linearize(p,tolerance=0.001):
    '''
    This function recieves a component of a 'cubicsuperpath' and returns two things:
    The path subdivided in many straight segments, and an array containing the length of each segment.
    
    We could work with bezier path as well, but bezier arc lengths are (re)computed for each point 
    in the deformed object. For complex paths, this might take a while.
    '''
    zero=0.000001
    i=0
    d=0
    lengths=[]
    while i<len(p)-1:
        box  = bezmisc.pointdistance(p[i  ][1],p[i  ][2])
        box += bezmisc.pointdistance(p[i  ][2],p[i+1][0])
        box += bezmisc.pointdistance(p[i+1][0],p[i+1][1])
        chord = bezmisc.pointdistance(p[i][1], p[i+1][1])
        if (box - chord) > tolerance:
            b1, b2 = bezmisc.beziersplitatt([p[i][1],p[i][2],p[i+1][0],p[i+1][1]], 0.5)
            p[i  ][2][0],p[i  ][2][1]=b1[1]
            p[i+1][0][0],p[i+1][0][1]=b2[2]
            p.insert(i+1,[[b1[2][0],b1[2][1]],[b1[3][0],b1[3][1]],[b2[1][0],b2[1][1]]])
        else:
            d=(box+chord)/2
            lengths.append(d)
            i+=1
    new=[p[i][1] for i in range(0,len(p)-1) if lengths[i]>zero]
    new.append(p[-1][1])
    lengths=[l for l in lengths if l>zero]
    return(new,lengths)
    
def addDot(self,idPoint,labelPoint,diametre,typepoint):
        
    dot = inkex.etree.Element(inkex.addNS('path','svg'))
    dot.set('id',idPoint)
    cercle='M dia,0 A dia,dia 0 0 1 0,dia dia,dia 0 0 1 -dia,0 dia,dia 0 0 1 0,-dia dia,dia 0 0 1 dia,0 Z'
    ligneH='M 0,0 H dia'
    ligneV='M 0,0 V dia'
    rayon=ligneH.replace('dia',str(self.unittouu(diametre))) #valeur par defaut.
    if typepoint=="LigneV":
        rayon=ligneV.replace('dia',str(self.unittouu(diametre)))
    if typepoint=="Cercle":
        rayon=cercle.replace('dia',str(self.unittouu(diametre)/2))
    dot.set('d',rayon)
    dot.set('style', simplestyle.formatStyle({ 'stroke': '#7d7dff', 'fill': 'none','stroke-opacity':'1', 'stroke-width': str(self.unittouu('1px')) }))
    dot.set(inkex.addNS('label','inkscape'), labelPoint)
    self.current_layer.append(dot)
         
def addText(self,x,y,text):
    new = inkex.etree.Element(inkex.addNS('text','svg'))
    new.set('style', "font-style:normal;font-weight:normal;font-size:10px;line-height:100%;font-family:sans-serif;letter-spacing:0px;word-spacing:0px;fill:#000000;fill-opacity:1;stroke:none;stroke-width:1px;stroke-linecap:butt;stroke-linejoin:miter;stroke-opacity:1")#simplestyle.formatStyle(s))
    new.set('x', str(x))
    new.set('y', str(y))
    new.text = str(text)   
    self.current_layer.append(new)
    return new
        
class Pointsellier(pathmodifier.Diffeo):
    def __init__(self):
        pathmodifier.Diffeo.__init__(self)
        self.OptionParser.add_option("--title")
        
        self.OptionParser.add_option("--diamlong",
                        action="store", type="string", 
                        dest="diamlong", default="1.0mm")
        
        self.OptionParser.add_option("--typePoint",
                        action="store", type="string", 
                        dest="typePoint", default="LigneH")
        
        self.OptionParser.add_option("--textInfos",
                        action="store", type="inkbool", 
                        dest="textInfos", default=False)            
            
        self.OptionParser.add_option("-t", "--toffset",
                        action="store", type="string", 
                        dest="toffset", default="0.1mm")
        
        self.OptionParser.add_option("-p", "--space",
                        action="store", type="string", 
                        dest="space", default="3.0mm")
        
        self.OptionParser.add_option("--autoOffset",
                        action="store", type="inkbool", 
                        dest="autoOffset", default=False)   
        
        self.OptionParser.add_option("-r", "--nrepeat",
                        action="store", type="int", 
                        dest="nrepeat", default=1,help="nombre dobjet")
        
        self.OptionParser.add_option("--autoRepeat",
                        action="store", type="inkbool", 
                        dest="autoRepeat", default=False)            
                    
        self.OptionParser.add_option("--tab",
                        action="store", type="string",
                        dest="tab",
                        help="The selected UI-tab when OK was pressed")
        
           
    def lengthtotime(self,l):
        '''
        Recieves an arc length l, and returns the index of the segment in self.skelcomp 
        containing the coresponding point, to gether with the position of the point on this segment.

        If the deformer is closed, do computations modulo the toal length.
        '''
        if self.skelcompIsClosed:
            l=l % sum(self.lengths)
        if l<=0:
            return 0,l/self.lengths[0]
        i=0
        while (i<len(self.lengths)) and (self.lengths[i]<=l):
            l-=self.lengths[i]
            i+=1
        t=l/self.lengths[min(i,len(self.lengths)-1)]
        return i, t

    def applyDiffeo(self,bpt,vects=()):
        '''
        The kernel of this stuff:
        bpt is a base point and for v in vectors, v'=v-p is a tangent vector at bpt.
        '''
        s=bpt[0]-self.skelcomp[0][0]
        i,t=self.lengthtotime(s)
        if i==len(self.skelcomp)-1:#je regarde si je suis au debut du skelete car sinon j'ai pas de vecteur
            x,y=bezmisc.tpoint(self.skelcomp[i-1],self.skelcomp[i],1+t)
            dx=(self.skelcomp[i][0]-self.skelcomp[i-1][0])/self.lengths[-1]
            dy=(self.skelcomp[i][1]-self.skelcomp[i-1][1])/self.lengths[-1]
        else:
            x,y=bezmisc.tpoint(self.skelcomp[i],self.skelcomp[i+1],t)
            dx=(self.skelcomp[i+1][0]-self.skelcomp[i][0])/self.lengths[i]
            dy=(self.skelcomp[i+1][1]-self.skelcomp[i][1])/self.lengths[i]
        
        vx=0
        vy=bpt[1]-self.skelcomp[0][1]
        bpt[0]=x+vx*dx-vy*dy
        bpt[1]=y+vx*dy+vy*dx
        
        for v in vects:
            vx=v[0]-self.skelcomp[0][0]-s
            vy=v[1]-self.skelcomp[0][1]
            v[0]=x+vx*dx-vy*dy
            v[1]=y+vx*dy+vy*dx
            
    def effect(self):
        
        
        if len(self.options.ids)<1 and len(self.options.ids)>1:
            inkex.errormsg(_("This extension requires only one selected paths."))
            return
   #liste des chemins, preparation     
        idList=self.options.ids
        idList=pathmodifier.zSort(self.document.getroot(),idList)
        id = idList[-1]
        idpoint=id+'-'+ str(random.randint(1, 99)) #id du paterns creer a partir du chemin selectionner
        
        for id, node in self.selected.iteritems():
            style = simplestyle.parseStyle(node.get('style')) #je recupere l'ancien style
            style['stroke']='#00ff00' #je modifie la valeur
            node.set('style', simplestyle.formatStyle(style) ) #j'applique la modifi
        
        
        #gestion du skelte (le chemin selectionner)
        self.skeletons=self.selected
        self.expandGroupsUnlinkClones(self.skeletons, True, False)
        self.objectsToPaths(self.skeletons)
        
        for skelnode in self.skeletons.itervalues(): #calcul de la longeur du chemin
            self.curSekeleton=cubicsuperpath.parsePath(skelnode.get('d'))
            for comp in self.curSekeleton:
                self.skelcomp,self.lengths=linearize(comp)
                longeur=sum(self.lengths)
                
        distance=self.unittouu(self.options.space)
        taille= self.unittouu(self.options.diamlong)
        
        if self.options.autoRepeat: #gestion du calcul auto
            nbrRepeat=int(round((longeur)/distance))
        else:
            nbrRepeat=self.options.nrepeat
            
        if self.options.autoOffset: #gestion du decallage automatique
            tOffset=((longeur-(nbrRepeat-1)*distance)/2)-taille/2
        else:
            tOffset=self.unittouu(self.options.toffset)
            
        #gestion du paterns
        labelpoint='Point:'+self.options.diamlong+' Ecart:'+self.options.space + ' Decallage:' + str(round(self.uutounit(tOffset,'mm'),2))+'mm' + ' Nbr:' + str(nbrRepeat)+' longueur:'+str(round(self.uutounit(longeur,'mm'),2))+'mm'
        addDot(self,idpoint,labelpoint,self.options.diamlong,self.options.typePoint)#creation du cercle de base
        self.patterns={idpoint:self.getElementById(idpoint)} #ajout du point dans le paterns de base
  
        bbox=simpletransform.computeBBox(self.patterns.values())
   #liste des chemins, fin de preparation   

        if distance < 0.01:
            exit(_("The total length of the pattern is too small :\nPlease choose a larger object or set 'Space between copies' > 0"))

        for id, node in self.patterns.iteritems():

            if node.tag == inkex.addNS('path','svg') or node.tag=='path':
                d = node.get('d')
                p0 = cubicsuperpath.parsePath(d)
                newp=[]
                for skelnode in self.skeletons.itervalues(): 
                    self.curSekeleton=cubicsuperpath.parsePath(skelnode.get('d'))
                    for comp in self.curSekeleton:
                        p=copy.deepcopy(p0)
                        self.skelcomp,self.lengths=linearize(comp)
                        #!!!!>----> TODO: really test if path is closed! end point==start point is not enough!
                        self.skelcompIsClosed = (self.skelcomp[0]==self.skelcomp[-1])

                        length=sum(self.lengths)
                        xoffset=self.skelcomp[0][0]-bbox[0]+tOffset
                        yoffset=self.skelcomp[0][1]-(bbox[2]+bbox[3])/2
                        if self.options.textInfos:
                            addText(self,xoffset,yoffset,labelpoint)
                        MaxCopies=max(1,int(round((length+distance)/distance)))
                        NbCopies= nbrRepeat #nombre de copie desirer a intergrer dans les choix a modifier pour ne pas depasser les valeurs maxi
                        if NbCopies > MaxCopies:
                            NbCopies=MaxCopies #on limitte le nombre de copie au maxi possible sur le chemin
                        width=distance*NbCopies
                        if not self.skelcompIsClosed:
                            width-=distance

                        new=[]
                        for sub in p: #creation du nombre de patern
                            for i in range(0,NbCopies,1):
                                new.append(copy.deepcopy(sub)) #realise une copie de sub pour chaque nouveau element du patern
                                offset(sub,distance,0)
                        p=new
                        for sub in p:
                            offset(sub,xoffset,yoffset)
                        for sub in p: #une fois tous creer, on les mets en place    
                            for ctlpt in sub:#pose le patern sur le chemin
                                    self.applyDiffeo(ctlpt[1],(ctlpt[0],ctlpt[2]))
                           
                        newp+=p

                node.set('d', cubicsuperpath.formatPath(newp))

if __name__ == '__main__':
    e = Pointsellier()
    e.affect()

                    
# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 fileencoding=utf-8 textwidth=99
