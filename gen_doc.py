from subprocess import run
from os import chdir,rename
from shutil import rmtree
from time import sleep

run(['doxygen','Doxyfile'], check=True)
sleep(1)
chdir('doc/latex')
run(['pdflatex','refman'])
rename('refman.pdf','../espy_documentation.pdf')
chdir('..')
rmtree('latex')

