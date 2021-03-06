Daniel Spavin
daniel@spavin.net


Version Support
7.2, 7.1, 7.0, 6.6, 6.5, 6.4

Who is this app for?
This app is for anyone who wants to visualise and correlate multiple separate events on a common timeline.

How does the app work?
This app provides a visualization that you can use in your own apps and dashboards.

To use it in your dashboards, simply install the app, and create a search that provides the values you want to display.

Usecases for the Event Timeline Visualization:
Displaying time-based events
Comparing the duration and severity of incident tickets created over the past month
Tracking production releases and version information over time
Visualizing server metrics over hours or days
Tracking Notable Events over time
The following fields can be used in the search:
label (required): A title for the event being displayed.
start (required): A date and time indicating the start of the event
end (optional): A data and time indicating the end of the event
group (optional): A group name to categorise the events and display them together
color (optional): This is usually generated by the rangemap command. It is used to set the color for the slide. Valid colors are: red, amber, green. If using rangemap, use 'range' instead of 'color'. Valid values include: low, elevated, severe, ok, warning, etc
data (optional): A value to use for drilldowns, which is not displayed to the user, e.g. ID numbers, references, sources. The data field will be used to populate the $tok_et_data$ token.
Example Search
| makeresults count=25 
| eval start=_time-random()% 7*24*60*60 
| streamstats count as id
| eval label=case(id%3=0,"Event A", id%5=0,"Event B", id%7=0,"Event C", id%11=0,"Event D",1=1,"Event E")
| eval range=if(random()%2=0,"low","severe")
| table start, label, range

Tokens
This visualization generates the following tokens on click:

Start field - defaults to: $tok_et_start$
End field - defaults to: $tok_et_end$
Data field - defaults to: $tok_et_data$
Label field - defaults to: $tok_et_label$
All Visible Events' Data field - defaults to: $tok_et_all_visible$
Note: all token names are customisable in the visualization settings menu.

Limits
The visualization is bound by the following limits:

Total results: 10,000
# Release Notes #
v 1.0.0
Initial version
Issues and Limitations
No issues identified.
If you have a bug report or feature request, please contact daniel@spavin.net

Privacy and Legal
No personally identifiable information is logged or obtained in any way through this visualizaton.

For support
Send email to daniel@spavin.net

Support is not guaranteed and will be provided on a best effort basis.

Credits
This visualization uses the vis.js visualization library.