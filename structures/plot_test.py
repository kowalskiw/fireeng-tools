import matplotlib.pyplot as plt
import numpy as np

class DomainPlot:
	def __init__(self, domain, points):
		self.domain = domain
		self.points = points

		d = self.domain

		self.domain_points = [
			[d[0],d[2],d[4]],
			[d[1],d[2],d[4]],
			[d[1],d[3],d[4]],
			[d[0],d[3],d[4]],
			[d[0],d[2],d[5]],
			[d[1],d[2],d[5]],
			[d[1],d[3],d[5]],
			[d[0],d[3],d[5]],
		]

		xa = self.domain[0]
		xb = self.domain[1]
		ya = self.domain[2]
		yb = self.domain[3]
		za = self.domain[4]
		zb = self.domain[5]

		self.lines =[
		#za const - lower
			([xa,xb],[ya,ya],[za,za]), #a
			([xb,xb],[ya,yb],[za,za]), #b
			([xa,xb],[yb,yb],[za,za]), #c
			([xa,xa],[ya,yb],[za,za]), #d
			#zb const - upper
			([xa,xb],[ya,ya],[zb,zb]), #e
			([xb,xb],[ya,yb],[zb,zb]), #f
			([xa,xb],[yb,yb],[zb,zb]), #g
			([xa,xa],[ya,yb],[zb,zb]), #h
			#horizontal za != zb
			([xa,xa],[ya,ya],[za,zb]), #i
			([xb,xb],[ya,ya],[za,zb]), #j
			([xb,xb],[yb,yb],[za,zb]), #k
			([xa,xa],[yb,yb],[za,zb]) #l
		] 
		self.aaa = ""
		
			
			


	def show_plot(self):
		fig = plt.figure()
		ax = fig.add_subplot(projection='3d')

		for line in self.lines:
			ax.plot(*line, color='black')

		ax.set_xlabel('X Label')
		ax.set_ylabel('Y Label')
		ax.set_zlabel('Z Label')

		plt.show()
		
		#domain   [0-XA, 1-XB, 2-YA, 3-YB, 4-ZA, 5-ZB]
domain = [10.175, 10.925, 27.125, 27.525, 2.525, 3.225]
points =[1,2,3]


d = DomainPlot(domain, points).show_plot()
