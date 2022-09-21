from dataclasses import dataclass
from typing import Any, Callable, Generic, Literal, NamedTuple, Sequence, TypeVar, Union

import numpy as np
import matplotlib.pyplot as plt
from muutils.tensor_utils import ATensor, NDArray, DTYPE_MAP

from maze_transformer.generation.latticemaze import LatticeMaze

def plot_path(maze: LatticeMaze, path: NDArray, show: bool = True) -> None:
	# print(m)
	# show the maze
	img = maze.as_img()
	path_transformed = maze.points_transform_to_img(path)

	# plot path
	plt.plot(*zip(*path_transformed), "-", color="red")
	# mark endpoints
	plt.plot([path_transformed[0][0]], [path_transformed[0][1]], "o", color="red")
	plt.plot([path_transformed[-1][0]], [path_transformed[-1][1]], "x", color="red")
	# show actual maze
	plt.imshow(img.T, cmap="gray", vmin=-1, vmax=1)

	if show:
		plt.show()

@dataclass
class PathFormat:
	"""formatting options for path plot
	(path_true, "true", "-", "red")
	"""
	path: NDArray
	label: str|None = None
	fmt: str|None = None
	color: str|None = None

def plot_multi_paths(
		maze: LatticeMaze, 
		paths: list[PathFormat|tuple|list],
		use_quiver: bool = True,
		show: bool = True,
	) -> None:

	# show the maze
	img = maze.as_img()
	plt.imshow(
		np.rot90(img, 1),
		cmap = "gray",
		extent = [
			-0.75, maze.grid_shape[0] - 1 + 0.75, 
			-0.75, maze.grid_shape[1] - 1 + 0.75,
		],
	)

	# plot paths
	for pf in paths:
		
		if isinstance(pf, (tuple, list)):
			pf = PathFormat(*pf)

		# p_transformed: NDArray = maze.points_transform_to_img(pf.path)
		p_transformed: NDArray = pf.path

		if use_quiver:
			x: NDArray = p_transformed[:, 0]
			y: NDArray = p_transformed[:, 1]
			plt.quiver(x[:-1], y[:-1], x[1:]-x[:-1], y[1:]-y[:-1], scale_units='xy', angles='xy', scale=1, color=pf.color)
		else:
			plt.plot(*zip(*p_transformed), pf.fmt, color=pf.color, label=pf.label)
		# mark endpoints
		plt.plot([p_transformed[0][0]], [p_transformed[0][1]], "o", color=pf.color)
		plt.plot([p_transformed[-1][0]], [p_transformed[-1][1]], "x", color=pf.color)

	if show:
		plt.show()
