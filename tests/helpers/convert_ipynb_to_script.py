import os
import json
import typing
import argparse

# TODO: make this work for plotly
DISABLE_PLOTS_CODE: list[str] = [
    '# ' + '-' * 80,
    '# Disable plots, done during processing by `convert_ipynb_to_script.py`',
    'import matplotlib.pyplot as plt',
    'plt.show = lambda: None',
    '# ' + '-' * 80,
]

    
def disable_plots_in_script(script_lines: list[str]) -> list[str]:
    """Disable plots in a script by adding cursed things after the import statements"""
    result_str_TEMP: str = '\n\n'.join(script_lines)
    if "matplotlib" in result_str_TEMP:
        assert "import matplotlib.pyplot as plt" in result_str_TEMP, "matplotlib.pyplot must be imported as plt"
        
        # find the last import statement involving matplotlib
        last_import_index: int = -1
        for i, line in enumerate(script_lines):
            if (
                "matplotlib" in line 
                and (("import" in line) or "from" in line)
            ):
                last_import_index = i
        assert last_import_index != -1, "matplotlib imports not found!"
        
        # check no plots are created before the import
        for i, line in enumerate(script_lines[:last_import_index]):
            assert "plt." not in line, "matplotlib plots created before import!"

        # insert the cursed things
        return script_lines[:last_import_index + 1] + DISABLE_PLOTS_CODE + script_lines[last_import_index + 1:]
    else:
        return script_lines

def convert_ipynb(
    notebook: dict, 
    strip_md_cells: bool = False,
    header_comment: str = r'#%%',
    disable_plots: bool = False,
    filter_out_lines: str|typing.Sequence[str] = ('%', '!'), # ignore notebook magic commands and shell commands
) -> str:
    """Convert Jupyter Notebook to a script, doing some basic filtering and formatting.

    # Arguments
        - `notebook: dict`: Jupyter Notebook loaded as json.
        - `strip_md_cells: bool = False`: Remove markdown cells from the output script.
        - `header_comment: str = r'#%%'`: Comment string to separate cells in the output script.
        - `disable_plots: bool = False`: Disable plots in the output script.
        - `filter_out_lines: str|typing.Sequence[str] = ('%', '!')`: comment out lines starting with these strings (in code blocks). 
            if a string is passed, it will be split by char and each char will be treated as a separate filter.

    # Returns
        - `str`: Converted script.
    """

    if isinstance(filter_out_lines, str):
        filter_out_lines = tuple(filter_out_lines)
    filter_out_lines_set: set = set(filter_out_lines)

    result: list[str] = []

    all_cells: list[dict] = notebook['cells']

    for cell in all_cells:

        cell_type: str = cell['cell_type']

        if not strip_md_cells and cell_type == 'markdown':
            result.append(f'{header_comment}\n"""\n{"".join(cell["source"])}\n"""')
        elif cell_type == 'code':
            source: list[str] = cell['source']
            if filter_out_lines:
                source = [
                    f'#{line}' 
                    if any(
                        line.startswith(filter_prefix) 
                        for filter_prefix in filter_out_lines_set
                    )
                    else line 
                    for line in source
                ]
            result.append(f'{header_comment}\n{"".join(source)}')

    if disable_plots:
        result = disable_plots_in_script(result)
            
    return '\n\n'.join(result)

def process_file(
    in_file: str,
    out_file: str|None = None,
    strip_md_cells: bool = False,
    header_comment: str = r'#%%',
    disable_plots: bool = False,
    filter_out_lines: str|typing.Sequence[str] = ('%', '!'),
):

    assert os.path.exists(in_file), f'File {in_file} does not exist.'
    assert os.path.isfile(in_file), f'Path {in_file} is not a file.'
    assert in_file.endswith('.ipynb'), f'File {in_file} is not a Jupyter Notebook.'

    with open(in_file, 'r') as file:
        notebook: dict = json.load(file)

    converted_script: str = convert_ipynb(
        notebook=notebook,
        strip_md_cells=strip_md_cells,
        header_comment=header_comment,
        disable_plots=disable_plots,
        filter_out_lines=filter_out_lines,
    )

    if out_file:
        with open(out_file, 'w') as file:
            file.write(converted_script)
    else:
        print(converted_script)

def process_dir(
    input_dir: str,
    output_dir: str,
    strip_md_cells: bool = False,
    header_comment: str = r'#%%',
    disable_plots: bool = False,
    filter_out_lines: str|typing.Sequence[str] = ('%', '!'),
):
    """Convert all Jupyter Notebooks in a directory to scripts.

    # Arguments
        - `input_dir: str`: Input directory.
        - `output_dir: str`: Output directory.
        - `strip_md_cells: bool = False`: Remove markdown cells from the output script.
        - `header_comment: str = r'#%%'`: Comment string to separate cells in the output script.
        - `disable_plots: bool = False`: Disable plots in the output script.
        - `filter_out_lines: str|typing.Sequence[str] = ('%', '!')`: comment out lines starting with these strings (in code blocks). 
            if a string is passed, it will be split by char and each char will be treated as a separate filter.
    """

    assert os.path.exists(input_dir), f'Directory {input_dir} does not exist.'
    assert os.path.isdir(input_dir), f'Path {input_dir} is not a directory.'

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    filenames: list[str] = [
        fname for fname in os.listdir(input_dir)
        if fname.endswith('.ipynb')
    ]

    assert filenames, f'Directory {input_dir} does not contain any Jupyter Notebooks.'

    for fname in filenames:
        in_file: str = os.path.join(input_dir, fname)
        out_file: str = os.path.join(output_dir, fname.replace(".ipynb", ".py"))

        with open(in_file, 'r', encoding='utf-8') as file_in:
            notebook: dict = json.load(file_in)

        converted_script: str = convert_ipynb(
            notebook=notebook,
            strip_md_cells=strip_md_cells,
            header_comment=header_comment,
            disable_plots=disable_plots,
            filter_out_lines=filter_out_lines,
        )

        with open(out_file, 'w', encoding='utf-8') as file_out:
            file_out.write(converted_script)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert Jupyter Notebook to a script with cell separators.')
    parser.add_argument('in_path', type=str, help='Input Jupyter Notebook file (.ipynb) or directory of files.')
    parser.add_argument('--out_file', type=str, help='Output script file. If not specified, the result will be printed to stdout.')
    parser.add_argument('--output_dir', type=str, help='Output directory for converted script files.')
    parser.add_argument('--strip_md_cells', action='store_true', help='Remove markdown cells from the output script.')
    parser.add_argument('--header_comment', type=str, default=r'#%%', help='Comment string to separate cells in the output script.')
    parser.add_argument('--disable_plots', action='store_true', help='Disable plots in the output script. Useful for testing in CI.')
    parser.add_argument('--filter_out_lines', type=str, default='%', help='Comment out lines starting with these characters.')

    args = parser.parse_args()

    if args.output_dir:
        assert not args.out_file, 'Cannot specify both --out_file and --output_dir.'
        process_dir(
            input_dir=args.in_path,
            output_dir=args.output_dir,
            strip_md_cells=args.strip_md_cells,
            header_comment=args.header_comment,
            disable_plots=args.disable_plots,
            filter_out_lines=args.filter_out_lines,
        )

    else:
        process_file(
            in_file=args.in_path,
            out_file=args.out_file,
            strip_md_cells=args.strip_md_cells,
            header_comment=args.header_comment,
            disable_plots=args.disable_plots,
            filter_out_lines=args.filter_out_lines,
        )
    