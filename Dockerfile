FROM scipoptsuite/scipoptsuite:7.0.2

RUN python -m pip install --upgrade pip
RUN python -m pip install statsmodels scikit-learn deepdiff pytest

WORKDIR /app
ENV PYTHONPATH=$PYTHONPATH:/app
COPY . ./

