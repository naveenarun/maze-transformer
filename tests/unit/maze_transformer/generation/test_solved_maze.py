import pytest

from maze_transformer.generation.generators import LatticeMazeGenerators
from maze_transformer.generation.latticemaze import SolvedMaze
from maze_transformer.training.mazedataset import MazeDatasetConfig
from maze_transformer.training.tokenizer import maze_to_tokens


@pytest.mark.skip(
    "Currently impossible to compare LatticeMazes - https://github.com/AISC-understanding-search/maze-transformer/issues/135"
)
def test_from_tokens():
    maze_size = 2
    maze, solution = LatticeMazeGenerators.gen_dfs_with_solution((maze_size, maze_size))

    # See https://github.com/AISC-understanding-search/maze-transformer/issues/77
    config = MazeDatasetConfig(grid_n=maze_size, name="test", n_mazes=1)
    tokenized_maze = maze_to_tokens(maze, solution, config.node_token_map)

    new_maze, new_solution = SolvedMaze.from_tokens(tokenized_maze, config)
    assert new_maze == maze
    assert new_solution == solution
