from setuptools import setup, find_packages

setup(
    name='gold_quant_toolkit',
    version='1.0.0',
    description='A comprehensive toolkit for gold quantitative trading strategies',
    author='GoldQuant Team',
    author_email='goldquant@example.com',
    packages=find_packages(),
    install_requires=[
        'pandas>=1.5.0',
        'numpy>=1.24.0',
        'yfinance>=0.2.0',
        'scipy>=1.10.0'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: Financial and Insurance Industry',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Programming Language :: Python :: 3.10',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Office/Business :: Financial :: Investment'
    ],
    python_requires='>=3.8',
    include_package_data=True,
    zip_safe=False
)