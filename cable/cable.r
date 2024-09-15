# https://www.cincibrainlab.com/post/efficiently-move-data-between-matlab-and-r/
install.packages(c("tidyverse", "R.matlab"))
library(tidyverse)
library(R.matlab)
library(ggplot2)
filename <- "/Users/keeney/pen-bay-marine-data/cable/hurricane-scientific-mooring.mat"
results <- R.matlab::readMat(filename)
df <- data.frame(results)
df |> ggplot(aes(x = x, y = z)) + 
    geom_point(aes(color = T)) + 
    geom_hline(yintercept=df$depth[0:1], linetype="solid", color = "black") + 
    geom_hline(yintercept=0, linetype="solid", color = "black") + 
    geom_hline(yintercept=max(df$z), linetype="dashed", color = "black") +
    geom_vline(xintercept=max(df$x), linetype="dashed", color = "black") +
    scale_x_continuous(breaks = seq(0, max(df$x), by = 2)) +
    scale_y_continuous(breaks = seq(0, df$depth[0:1], by = 2)) +
    coord_fixed() + 
    theme_linedraw() +
    labs(
        # title = "Mooring static analysis",
        x = "X (m)",
        y = "Z (m)",
        color = "Tension (N)"
    )