#!/usr/bin/env python 
'''
Copyright (C) 2005 Aaron Spike, aaron@ekips.org

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
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
'''
import inkex, simplestyle, simplepath, math

class Dots(inkex.Effect):

    def __init__(self):
        inkex.Effect.__init__(self)
        self.OptionParser.add_option("-d", "--dotsize",
                        action="store", type="string",
                        dest="dotsize", default="3mm",
                        help="Size of the dots placed at path nodes")
        self.OptionParser.add_option("--tab",
                        action="store", type="string",
                        dest="tab",
                        help="The selected UI-tab when OK was pressed")

    def effect(self):
        selection = self.selected
        if (selection):
            for id, node in selection.iteritems():
                if node.tag == inkex.addNS('path','svg'):
                    self.addDot(node)
        else:
            inkex.errormsg("Please select an object.")

    def separateLastAndFirst(self, p):
        # Separate the last and first dot if they are togheter
        lastDot = -1
        if p[lastDot][1] == []: lastDot = -2
        if round(p[lastDot][1][-2]) == round(p[0][1][-2]) and \
                round(p[lastDot][1][-1]) == round(p[0][1][-1]):
                x1 = p[lastDot][1][-2]
                y1 = p[lastDot][1][-1]
                x2 = p[lastDot-1][1][-2]
                y2 = p[lastDot-1][1][-1]
                dx = abs( max(x1,x2) - min(x1,x2) )
                dy = abs( max(y1,y2) - min(y1,y2) )
                dist = math.sqrt( dx**2 + dy**2 )
                x = dx/dist
                y = dy/dist
                if x1 > x2: x *= -1
                if y1 > y2: y *= -1
                p[lastDot][1][-2] += x 
                p[lastDot][1][-1] += y 

    def addDot(self, node):
        
        self.dotGroup = inkex.etree.SubElement( node.getparent(), inkex.addNS('g','svg') )
        self.dotGroup.set(inkex.addNS('label','inkscape'), 'gabarit: ' + self.options.dotsize)
        
        try:
            t = node.get('transform')
            self.dotGroup.set('transform', t)
        except:
            pass

        style = simplestyle.formatStyle({ 'stroke': '#00ff00', 'fill': 'none' ,'stroke-width': str(self.unittouu('1px'))})
        a = []
        p = simplepath.parsePath(node.get('d'))

        #self.separateLastAndFirst(p)

        for cmd,params in p:
            if cmd != 'Z' and cmd != 'z':
                dot_att = {
                  'style': style,
                  'width': str( self.unittouu(self.options.dotsize)*2 ),
                  'height': str( self.unittouu(self.options.dotsize)*2 ),
                  'x': str( params[-2]-self.unittouu(self.options.dotsize) ),
                  'y': str( params[-1] -self.unittouu(self.options.dotsize) )
                }
                
                inkex.etree.SubElement(
                  self.dotGroup,
                  inkex.addNS('rect','svg'),
                  dot_att )
        
    
if __name__ == '__main__':
    e = Dots()
    e.affect()


# vim: expandtab shiftwidth=4 tabstop=8 softtabstop=4 fileencoding=utf-8 textwidth=99
