from setuptools import setup

tests_requirements = ['pyvows>=1.0.0', 'tornado_pyvows>=0.4.0']

setup(
    name='trombi',
    version='0.9.2',
    description='CouchDB client for Tornado',
    license='MIT',
    author='Jyrki Pulliainen',
    author_email='jyrki@dywypi.org',
    maintainer='Jyrki Pulliainen',
    maintainer_email='jyrki@dywypi.org',
    url='http://github.com/inoi/trombi/',
    packages=['trombi'],
    install_requires = [
        'tornado>=2.2',
        ],
    tests_require = tests_requirements,
    extras_require = {'test': tests_requirements},
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.2',
        'Topic :: Database',
        ]
)
