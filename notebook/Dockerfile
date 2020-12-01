FROM jupyter/minimal-notebook

ADD --chown=jovyan:users . /src/nbexchange
RUN cd /src/nbexchange && python setup.py install
RUN pip install -e git+https://github.com/jupyter/nbgrader.git@master#egg=nbgrader-0.7.0.dev0

COPY notebook/requirements.txt /requirements.txt
RUN pip install -r /requirements.txt

RUN jupyter nbextension install --sys-prefix --py nbgrader && \
    jupyter nbextension enable --sys-prefix validate_assignment/main --section=tree && \
    jupyter serverextension enable --sys-prefix nbgrader.server_extensions.validate_assignment && \
    jupyter nbextension enable --sys-prefix assignment_list/main --section=tree && \
    jupyter serverextension enable --sys-prefix nbgrader.server_extensions.assignment_list && \
    jupyter nbextension enable --sys-prefix create_assignment/main && \
    jupyter nbextension enable --sys-prefix formgrader/main --section=tree && \
    jupyter serverextension enable --sys-prefix nbgrader.server_extensions.formgrader

COPY notebook/nbgrader_config.py /etc/jupyter/.

COPY notebook/jupyter_notebook_config.py /home/jovyan/.jupyter/jupyter_notebook_config.py
