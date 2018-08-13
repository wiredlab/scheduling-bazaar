


NOTEBOOKS=$(wildcard *.ipynb)

all: $(NOTEBOOKS)

#jupyter nbconvert --to notebook --execute observations-satellites.ipynb && mv observations-satellites.nbconvert.ipynb observations-satellites.ipynb

%.ipynb: ../data/*
	jupyter nbconvert --to notebook --execute $*.ipynb \
	    && mv $*.nbconvert.ipynb $*.ipynb
