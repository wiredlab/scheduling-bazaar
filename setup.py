import setuptools

with open('README.md', 'r') as fp:
    long_description = fp.read()

setuptools.setup(
    name='satbazaar',
    version='0.0.1',
    author='Dan White',
    author_email='dan.white@valpo.edu',
    long_description=long_description,
    long_desctiption_content_type='text/markdown',
    url='https://github.com/wiredlab/scheduling-bazaar',
    packages=setuptools.find_packages(),
    classifiers=(
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Operating System :: OS Independent',
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
    ),
)
