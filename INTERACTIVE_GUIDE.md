# 🎙️ Interactive Podcast Analysis - User Guide

## Features

Your interactive D3.js visualization includes:

### **📊 Multiple View Types**
- **Episode Comparison**: Side-by-side bars for each episode
- **Total Speaking Time**: Overall accumulated totals
- **Percentage View**: Stacked bars showing % breakdown
- **Timeline View**: Connected line chart showing trends

### **🔧 Interactive Controls**
- **Sort By**: Episode order, speaking time, total time, difference
- **Filter Episodes**: All, main episodes, SMLT series, specials
- **Animation Toggle**: Enable/disable smooth transitions

### **✨ Interactive Elements**
- **Hover Tooltips**: Detailed stats on mouse hover
- **Real-time Updates**: Instant filtering and sorting
- **Responsive Design**: Works on desktop, tablet, mobile
- **Beautiful Animations**: Smooth D3.js transitions

### **📈 Live Statistics Bar**
- Mark's total speaking time
- Scott's total speaking time  
- Number of episodes analyzed
- Current winner

## How to Use

1. **Open the Visualization**:
   ```bash
   # Open in your browser
   open interactive_analysis.html
   ```

2. **Explore Different Views**:
   - Start with "Episode Comparison" to see individual episodes
   - Switch to "Timeline View" to see trends over time
   - Try "Percentage View" for relative comparisons

3. **Filter and Sort**:
   - Filter by episode type (main, SMLT, specials)
   - Sort by different metrics to find patterns
   - Watch the stats update in real-time

4. **Interactive Exploration**:
   - Hover over bars/points for detailed tooltips
   - Toggle animations on/off based on preference
   - Use responsive design on any device

## Data Source

The visualization loads real data from `transcript_data.json`, which is generated from your actual podcast transcripts using:

```bash
python3 generate_json_data.py
```

This ensures the interactive charts always reflect your latest analysis!

## NY Times Style Features

✅ **Smooth D3.js animations**  
✅ **Interactive filtering and sorting**  
✅ **Beautiful hover tooltips**  
✅ **Responsive design**  
✅ **Real-time statistics**  
✅ **Multiple visualization types**  
✅ **Client-side only (no server required)**  

## Browser Compatibility

Works in all modern browsers:
- Chrome, Firefox, Safari, Edge
- Mobile browsers (iOS Safari, Chrome Mobile)
- Tablets and desktop computers

Enjoy exploring your podcast data! 🎉
