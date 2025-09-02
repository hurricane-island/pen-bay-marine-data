# https://www.cincibrainlab.com/post/efficiently-move-data-between-matlab-and-r/
install.packages(c("tidyverse", "R.matlab"))
library(tidyverse)
library(R.matlab)
library(ggplot2)

high <- data.frame(R.matlab::readMat("/Users/keeney/pen-bay-marine-data/cable/hurricane-scientific-mooring-high.mat"))
low <- data.frame(R.matlab::readMat("/Users/keeney/pen-bay-marine-data/cable/hurricane-scientific-mooring-low.mat"))
ggplot() + 
    geom_point(data=high, aes(x = x, y = z, color = T), size=0.5) + 
    geom_point(data=low, aes(x = x, y = z, color = T), size=0.5) + 
    scale_colour_gradient(low = "cyan", high = "magenta") +
    geom_hline(yintercept=high$depth[0:1], linetype="solid", color = "black") + 
    geom_hline(yintercept=0, linetype="solid", color = "black") + 
    # geom_hline(yintercept=max(high$z), linetype="dashed", color = "black") +
    geom_vline(xintercept=max(high$x), linetype="dashed", color = "black") +
    geom_hline(yintercept=low$depth[0:1], linetype="solid", color = "black") + 
    # geom_hline(yintercept=max(low$z), linetype="dashed", color = "black") +
    geom_vline(xintercept=max(low$x), linetype="dashed", color = "black") +
    scale_x_continuous(breaks = seq(0, max(low$x), by = 2)) +
    scale_y_continuous(breaks = seq(0, high$depth[0:1], by = 2)) +
    coord_fixed() + 
    theme_linedraw() +
    labs(
        x = "X (m)",
        y = "Z (m)",
        color = "Tension (N)"
    )