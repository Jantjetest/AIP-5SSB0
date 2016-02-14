import atexit, os, re, shutil

from lxml import html
from pathlib import Path

build_directory = 'bundle'

ipynb_files = []

# Only include ipynb files which are not checkpoints
ipynb_matcher = re.compile("(?<!checkpoint.)ipynb$")

for (directory, _, files) in os.walk('lessons'):
    for filename in files:
        filepath = Path(directory, filename)
        filepath_str = str(filepath)
        if ipynb_matcher.search(filepath_str):
            ipynb_files.append(filepath_str)
        else:
            target_path = Path(build_directory, *filepath.parts[2:])
            target_directory = Path(*target_path.parts[:-1])
            if not target_directory.exists():
                target_directory.mkdir(parents = True)
            shutil.copy(str(filepath), str(target_path))

# The chapters are not necessarily returned in order by the filesystem. Since
# the files have their order embedded in their filename, sorting them here
# should be sufficient
ipynb_files.sort()

# Some cells can take quite a while to render (most notably the lesson on
# clustering with Gaussian Mixture Models), so the timeout has to be increased
# with respect to the default of 30 seconds
c.ExecutePreprocessor.timeout = 120
c.FilesWriter.build_directory = build_directory
c.NbConvertApp.notebooks = ipynb_files
c.Preprocessor.enabled = True

def concat_and_clean():
    bundle_cells = []
    bundle_document = None
    notebook_root = None

    for source_path_str in ipynb_files:
        source_path = Path(source_path_str)
        bundle_path = Path(build_directory, source_path.stem + '.html')

        if bundle_path.exists():
            rendered_file = open(str(bundle_path), 'r', encoding='utf-8')
            html_source = html.fromstring(rendered_file.read())
            rendered_file.close()

            os.remove(str(bundle_path))

            cells = html_source.find_class('cell')

            # If no main document body is available yet, grab it from the first
            # page that is found. Use that as the basis for the entire bundle
            if bundle_document == None:
                bundle_document = html_source
                body_node = bundle_document.xpath('//body')[0]

                cover_file = open('./cover.html', 'r', encoding='utf-8')
                cover_source = html.fromstring(cover_file.read())
                cover_file.close()

                cover_styles = cover_source.xpath('//style')[0]
                bundle_head = bundle_document.xpath('//head')[0]
                bundle_head.insert(2, cover_styles)

                cover_page = cover_source.get_element_by_id('cover-page')
                body_node.insert(0, cover_page)

                # Include the custom styles once, which would have otherwise be
                # included by the final two cells in every rendered notebook
                bundle_file = open(str(Path('styles', 'aipstyle.html')), 'r')
                custom_style_elements = html.fragments_fromstring(bundle_file.read())
                bundle_file.close()

                for element in reversed(custom_style_elements):
                    body_node.insert(0, element)

                # Even though the final two cells will be ignored below they
                # have to be actually removed from the 'base' document to make
                # sure they don't show up at the top of the notebook
                notebook_root = html_source.get_element_by_id('notebook-container')
                notebook_root.remove(cells[-2])
                notebook_root.remove(cells[-1])

            # The final two cells of every rendered notebook are expected to
            # contain the code loading custom CSS, these are not necessary for
            # the bundled version and should therefore be removed
            chapter_node = html.fromstring('<section></section>')
            notebook_root.append(chapter_node)
            for cell in cells[0:-2]:
                chapter_node.append(cell)

    shutil.copy('./styles/bundle.css', str(Path(build_directory, 'custom.css')))

    if bundle_document != None:
        bundle_filename = str(Path(build_directory, 'bundle.html'))
        bundle_file = open(bundle_filename, 'w', encoding='utf-8')
        bundle_file.write(html.tostring(bundle_document).decode('utf-8'))
        bundle_file.close()

        os.system('phantomjs ./print_to_pdf.js bundle/bundle.html')

    shutil.rmtree(build_directory)

atexit.register(concat_and_clean)