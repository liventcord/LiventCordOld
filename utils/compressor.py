import os
from csscompressor import compress
from jsmin import jsmin

def minify_css(input_path, output_path):
    with open(input_path, 'r') as css_file:
        css_content = css_file.read()
        minified_css = compress(css_content)
    with open(output_path, 'w') as minified_file:
        minified_file.write(minified_css)

def minify_js(input_path, output_path):
    with open(input_path, 'r') as js_file:
        js_content = js_file.read()
        minified_js = jsmin(js_content)
    with open(output_path, 'w') as minified_file:
        minified_file.write(minified_js)

def minify_all_files_in_folder(folder_path, minify_function, file_extension):
    for filename in os.listdir(folder_path):
        if filename.endswith(file_extension) and not filename.endswith(f".min{file_extension}"):
            input_path = os.path.join(folder_path, filename)
            output_path = os.path.join(folder_path, f"{filename[:-len(file_extension)]}.min{file_extension}")
            minify_function(input_path, output_path)

if __name__ == "__main__":
    css_folder = '/home/ubuntu/liventcord/static'
    js_folder = '/home/ubuntu/liventcord/static'
    


    minify_all_files_in_folder(css_folder, minify_css, '.css')
    minify_all_files_in_folder(js_folder, minify_js, '.js')
