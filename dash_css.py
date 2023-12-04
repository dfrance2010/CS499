#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu 2023-11-30
Last updated on Sun 2023-12-03
version: 1.0
author: David France
email: david.france@snhu.edu
Purpose: CSS stylesheet created for Grazioso Salvare dashboard
"""

class CSS(object):
    """CSS style functions"""
    
    def input(self, height, width):
        return {'height': height, 
                'width': width, 
                'border-radius': '5px', 
                'border-width': '1px'}

    def button(self, height, width):
        return {'height': height,'width': width, 
                'border-radius': '8px', 
                'border-width': '2px', 
                'border-color': 'white',
                'background-color': '#c9134b',
                'color': 'white',
                'font-size': '15px',
                'font-weight': 'medium'}

    