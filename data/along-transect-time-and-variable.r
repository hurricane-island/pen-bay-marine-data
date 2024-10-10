# Generate some synthetic data to show an example of raster plot
install.packages("oce")
library(oce)
locations <- 10
distance <- seq(0, locations)
hours_per_year <- 365 * 24
total_hours <- 365 * 24
hour <- 0:total_hours
raster <- matrix(nrow=locations, ncol=total_hours)

fragment <- function(hour, distance) {
    diurnal <- cos((hour %% 24) / 24 * 2 * pi - pi) + 1
    annual <- 2 * cos(hour / hours_per_year * 2 * pi - pi) + 1
    northing <- 2 * distance / locations
    random <- 0.2*abs(rnorm(1))
    return(annual + diurnal + northing + random)
}

for (row in distance) {
    for (col in hour) {
        raster[row, col] <- fragment(col, row)
    }
}
nf <- layout( matrix(c(1,2), ncol=1) )
image(t(raster))
# filled.contour(t(raster))
