# ==============================================================================
# Project: Bristol Spatial Analysis - Burglary & Inequality
# Author: YIHENG PAN
# Description: 
#   1. Data cleaning and merging of raw crime data.
#   2. Correlation analysis between deprivation (IMD) and burglary density.
#   3. Spatial inequality analysis (Affluent areas near vs. far from deprived areas).
#   4. DBSCAN parameter tuning (K-distance plot).
# ==============================================================================

# ------------------------------------------------------------------------------
# 0. Setup and Libraries
# ------------------------------------------------------------------------------

# Clear environment
rm(list = ls())

# Set working directory (Recommended: Use R Project or set to source file location)
# setwd("YOUR/PATH/TO/Bristol_Spatial_Analysis_R") 

# Load necessary libraries
# Note: Install packages only if not already installed
if(!require(sf)) install.packages("sf")
if(!require(dbscan)) install.packages("dbscan")

library(sf)
library(dbscan)

# ------------------------------------------------------------------------------
# 1. Data Processing: Merge & Clean Raw Data
# ------------------------------------------------------------------------------

# Define path to raw data
RAW_DATA_DIR <- "./01_Raw_Crime"

# Get list of all CSV files (2021-2022)
file_list <- list.files(path = RAW_DATA_DIR, pattern = "*.csv", full.names = TRUE)

if(length(file_list) > 0) {
  # Read and bind all CSVs into one dataframe
  raw_data_list <- lapply(file_list, function(x) {
    read.csv(x, stringsAsFactors = FALSE, header = TRUE)
  })
  
  raw_data <- do.call(rbind, raw_data_list)
  
  # Filter for 'Burglary' only
  burglary_data <- raw_data[raw_data$Crime.type == "Burglary", ]
  
  # Remove rows with missing coordinates (NA)
  clean_data <- burglary_data[!is.na(burglary_data$Longitude) & 
                                !is.na(burglary_data$Latitude), ]
  
  # Export cleaned data for QGIS analysis
  write.csv(clean_data, "bristol_burglary_cleaned_merged.csv", row.names = FALSE)
  
  cat("Data cleaning complete. Exported merged file.\n")
} else {
  warning("No CSV files found in the specified directory.")
}

# ------------------------------------------------------------------------------
# 2. Statistical Analysis: Correlation (IMD vs Burglary)
# ------------------------------------------------------------------------------

# Read the processed data (Output from QGIS with IMD join)
# Note: Ensure filename matches your local file
data1 <- read.csv("bristol_burglary_data.csv", stringsAsFactors = FALSE)

# Rename columns for easier access (Replacing '.' with '_')
names(data1)[names(data1) == "IMD.decile"] <- "IMD_decile"
names(data1)[names(data1) == "IMD.score"]  <- "IMD_score"
names(data1)[names(data1) == "IMD.rank"]   <- "IMD_rank"

# Ensure variables are numeric
data1$IMD_decile <- as.numeric(data1$IMD_decile)
data1$IMD_score  <- as.numeric(data1$IMD_score)
data1$IMD_rank   <- as.numeric(data1$IMD_rank)
data1$Density    <- as.numeric(data1$Density)
data1$NUMPOINTS  <- as.numeric(data1$NUMPOINTS)

# Create an ordered factor for IMD decile (for plotting)
data1$IMD_decile_factor <- factor(data1$IMD_decile, 
                                  levels = 1:10, 
                                  ordered = TRUE)

# --- Normality Tests (Shapiro-Wilk) ---
# Check if data follows normal distribution (p < 0.05 means not normal)
shapiro.test(data1$Density)
shapiro.test(data1$NUMPOINTS)
shapiro.test(data1$IMD_score)
shapiro.test(data1$IMD_rank)

# --- Spearman Correlation (Non-parametric) ---
# Used because data is not normally distributed

# 1. IMD Decile vs Density
cor_decile_density <- cor.test(data1$IMD_decile, data1$Density, method = "spearman")
# 2. IMD Decile vs Count
cor_decile_count   <- cor.test(data1$IMD_decile, data1$NUMPOINTS, method = "spearman")
# 3. IMD Score vs Density
cor_score_density  <- cor.test(data1$IMD_score, data1$Density, method = "spearman")

# --- Plotting: Boxplot of Density by IMD Decile ---

# Setup plot margins
par(mar = c(6, 5, 4, 2) + 0.1, bg = "white")

boxplot(Density ~ IMD_decile_factor, 
        data    = data1,
        col     = "grey85", 
        border  = "grey20",
        xlab    = "IMD 2019 Decile (1 = Most Deprived, 10 = Least Deprived)",
        ylab    = "Burglary Density (incidents per km², 2021–2022)",
        main    = "Distribution of Burglary Density by IMD 2019 Decile",
        outpch  = 20, 
        outcex  = 0.8)

# Add correlation stats to the plot
rho1 <- round(cor_decile_density$estimate, 2)
pval1 <- format(cor_decile_density$p.value, digits=2, scientific = FALSE)
label_rq1 <- paste("Spearman's \u03c1 = ", rho1, ", p = ", pval1, sep="")

mtext(label_rq1, side = 1, line = 4.5, adj = 1, cex = 0.8, col = "grey30")


# ------------------------------------------------------------------------------
# 3. Spatial Inequality: Affluent LSOA Analysis (Near vs Far)
# ------------------------------------------------------------------------------

# Read Affluent LSOA data
aff_data <- read.csv("Affluent_LSOA_with_prox_group.csv", stringsAsFactors = FALSE)

# Create descriptive labels based on proximity column
aff_data$ProxGroupLabel <- NA 
aff_data$ProxGroupLabel[aff_data$NearDepriv == "affluent_near_depriv"] <- "Near deprivation (<500 m)"
aff_data$ProxGroupLabel[aff_data$NearDepriv != "affluent_near_depriv"] <- "Far from deprivation (>=500 m)"

# Set factor levels to control plot order
aff_data$ProxGroupLabel <- factor(aff_data$ProxGroupLabel, 
                                  levels = c("Near deprivation (<500 m)", 
                                             "Far from deprivation (>=500 m)"))

# Test for difference (Wilcoxon Rank Sum Test)
WT1 <- wilcox.test(Density ~ ProxGroupLabel, data = aff_data)

# Calculate medians for reporting
aggregate(aff_data$Density, by=list(aff_data$ProxGroupLabel), FUN = median)

# --- Plotting: Comparison Boxplot ---

# Define colors (Pink/Red for Near, Blue for Far)
colors3 <- c("#ffb3b3", "#a6c8ff") 

par(mar = c(6, 5, 4, 2) + 0.1, bg = "white")

boxplot(Density ~ ProxGroupLabel, 
        data   = aff_data,
        col    = colors3,
        border = "grey20",
        xlab   = "",
        ylab   = "Burglary Density (incidents per km², 2021–2022)",
        main   = "Burglary Density in Affluent LSOAs: Near vs Far from Deprivation")

# Add test results text
pval2  <- format(WT1$p.value, digits=3)
label3 <- paste("Mann-Whitney U, p = ", pval2, sep="")
mtext(label3, side = 1, line = 4.5, adj = 1, cex = 1, col = "grey30")

# Add significance marker (*)
# Adjust the coordinates (x=1.5, y=170) based on your actual data range!
text(1.5, 170, labels = "*", cex = 2, col = "black")


# ------------------------------------------------------------------------------
# 4. Clustering Prep: K-Distance Plot for DBSCAN
# ------------------------------------------------------------------------------

# Read shapefile (Output from QGIS)
# Ensure "burglary_bng.shp" is in the working directory
if(file.exists("burglary_bng.shp")) {
  point_data <- st_read("burglary_bng.shp")
  
  # Extract coordinates matrix
  coords <- st_coordinates(point_data)
  
  # Plot K-distance to find optimal Epsilon (eps)
  
  # Test 1: k = 20
  kNNdistplot(coords, k = 20)
  abline(h = 350, lty = 2, col = "red") # Visual guide for eps = 350
  title(main = "K-Distance Plot (k=20)")
  
  # Test 2: k = 30
  dev.new() # Open new window for second plot
  kNNdistplot(coords, k = 30)
  abline(h = 200, lty = 2, col = "blue") # Visual guide for eps = 200
  title(main = "K-Distance Plot (k=30)")
  
} else {
  warning("Shapefile 'burglary_bng.shp' not found.")
}