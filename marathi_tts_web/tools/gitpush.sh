#!/bin/bash

find . -name \*Zone.Identifier -type f -delete
git add .; git commit -m "updated the code"; git push
