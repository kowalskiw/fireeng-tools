import matplotlib.pyplot as plt
import numpy as np

class DomainPlot:
	def __init__(self, domains, points):
		self.domains = domains
		self.points = points

		fig = plt.figure()
		ax = fig.add_subplot(projection='3d')

		for domain in self.domains:
			d = domain

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

			xa = domain[0]
			xb = domain[1]
			ya = domain[2]
			yb = domain[3]
			za = domain[4]
			zb = domain[5]

			self.domain_lines =[
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

			for line in self.domain_lines:
				ax.plot(*line, color='black')

			ax.set_xlabel('X')
			ax.set_ylabel('Y')
			ax.set_zlabel('Z')

		plt.show()

domains = [[10.175, 10.925, 27.125, 27.525, 2.525, 3.225],
		[11.175, 12.925, 28.125, 27.525, 2.525, 3.225],
		[12.175, 11.925, 25.125, 26.525, 12.525, 13.225]]
points =[1,2,3]


d = DomainPlot(domains, points)
#if __name__=="__main__":
