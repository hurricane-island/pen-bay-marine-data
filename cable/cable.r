# https://www.cincibrainlab.com/post/efficiently-move-data-between-matlab-and-r/
install.packages(c("tidyverse", "R.matlab"))
library(tidyverse)
library(R.matlab)
library(ggplot2)
filename <- "/Users/keeney/pen-bay-marine-data/cable/hurricane-scientific-mooring.mat"
results <- R.matlab::readMat(filename)
df <- data.frame(results)
df |> ggplot(aes(x = x, y = z)) + geom_point(aes(color = T))