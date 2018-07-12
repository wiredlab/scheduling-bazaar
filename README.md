# scheduling-bazaar
Package to simulate space-ground scheduling schemes. 

This project will be used to find contacts, or "visible" passes, for ground stations and satellites. 
The contacts will be used to answer scheduling questions for a network of ground stations. 


# Prerequisites

* numpy
* ephem
* orbit
* intervaltree
* iso8601

`conda env update -f environment.yml`

Uses `direnv` tool to manage shell setup.


# Git LFS
The `data/` directory is a submodule which stores generated data for testing.
That submodule uses [Git Large File Storage](https://git-lfs.github.com/) and its use requires installation of a Git extension, see the link for more information.

Checkout by `git submodule update --init`
