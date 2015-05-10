    function loadXMLDoc(theURL)
    {
        xmlhttp=new XMLHttpRequest();
        xmlhttp.open("GET", theURL, false);
        xmlhttp.send();
    }
	var xmlhttp=false;
var svg;
var rowsa;
var columnsa;
var birds;
function step(){
        $.ajax({url: "step", success: function(result){
			document.getElementById("responseText").innerHTML  = result;
	//		document.getElementById("svg").innerHTML  ="";
	//		$('#responseText').html = result;
		rowsa = document.getElementById('rows').value
	columnsa = document.getElementById('columns').value
			draw(result,rowsa,columnsa);
			
        }});
		return false;
    }	


function draw(response,rowsa,columnsa){

		d3.selection.prototype.size = function() {
		var n = 0;
		this.each(function() { ++n; });
		return n;
		};
		var cellSize= 10;
		var w = cellSize*parseInt(columnsa),
		h = cellSize*parseInt(rowsa),
		
		r = cellSize / 2,
		ssz = cellSize * cellSize,
		v = 3,
		t = 5000;

	var rows = Math.ceil(h / cellSize);
	var cols = Math.ceil(w / cellSize);



	var cells = d3.range(0, rows * cols).map(function (d) {
	  var col = d % cols;
	  var row = (d - col) / cols;
	  return {
		r: row,
		c: col,
		x: col * cellSize,
		y: row * cellSize ,
		p: response.charAt(row*cols+col)
	  };
	});
	var svg = d3.select("body").select("svg")
		.attr("width", w)
		.attr("height", h);



	var rectx = function(d) { return d.x - r; };
	var recty = function(d) { return d.y - r; };



	var cell = svg.selectAll(".cell")
	  .data(cells)
	  .enter().append("rect")
	  .attr("class", function(d) { return "cell " + ((d.p != ' ' && d.p!='-' && d.p!='|') ? "wall" : "air"); })
	  .attr("x", rectx)
	  .attr("y", recty)
	  .attr("width", cellSize)
	  .attr("height", cellSize)
	  .each(function(d) {
		d.elnt = d3.select(this);
	  });
}
	
 


window.onload=function() {

    document.getElementById('form').onsubmit=function() {
	 rowsa = document.getElementById('rows').value
	 columnsa = document.getElementById('columns').value
	 birds = document.getElementById('birds').value
	
	loadXMLDoc('new/'+rowsa+"/"+columnsa+"/"+birds);
	if(xmlhttp==false){alert("No response" )}
	else {
	var response = xmlhttp.responseText;
	rowsa = document.getElementById('rows').value
	columnsa = document.getElementById('columns').value
	birds = document.getElementById('birds').value
	}

    return false;
  }
	//$(document).ready(function(){	$("#step").click(step());});
    document.getElementById('step').onclick=step();
    document.getElementById('play').onclick=function(){
	while(true){
	step();
	}
 };
}