FROM continuumio/miniconda3 AS build
RUN conda install -y -c conda-forge ioos_qc
COPY ./main.py qartod/main.py
CMD [ "python3", "./qartod/main.py" ]