FROM continuumio/miniconda3 AS build
RUN conda install -y -c conda-forge ioos_qc
COPY ./main.py ioos_qc/main.py
CMD [ "python3", "./ioos_qc/main.py" ]