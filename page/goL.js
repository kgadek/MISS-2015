var goL = (function(){
  var goL ={},bits=128*256;
  var dt; // grid bits
  var dtB; // grid bits [block]
  var i;  // which dt is current?
  var sp=0; // speed of animation. smaller = faster.
  var timeClr ;// for clearing Timeout.
  var editMode=false;
  
  goL.clearGrid = function(){
    dt = [  Array.apply(0, Array(bits/32)).map(function() { return 0; }),
        Array.apply(0, Array(bits/32)).map(function() { return 0; })];
    dtB = [  Array.apply(0, Array(bits/32)).map(function() { return 0; }),
        Array.apply(0, Array(bits/32)).map(function() { return 0; })];
    i =0;// 0 is current
  }
  
  goL.get = function(p){ // get status of pth bit
    return (dt[i][p>>>5]&(0x80000000>>>(p&31))) ==0?0:1;
  }
  
  goL.put = function(p,s,j){ // set status of pth bit to s
    s ? (dt[j][p>>>5]|=(0x80000000>>>(p&31))): (dt[j][p>>>5]&=~(0x80000000>>>(p&31)));
  }

  goL.getB = function(p){ // get status of pth bit
    return (dtB[i][p>>>5]&(0x80000000>>>(p&31))) ==0?0:1;
  }
  
  goL.putB = function(p,s,j){ // set status of pth bit to s
    s ? (dtB[j][p>>>5]|=(0x80000000>>>(p&31))): (dtB[j][p>>>5]&=~(0x80000000>>>(p&31)));
  }
  
  goL.clearTimeout = function(){
    clearTimeout(timeClr);
  }
  
  goL.editMode = function(f){
    editMode=f;
    f? rects.attr('class',"edit") : rects.attr('class',"");
  }

  goL.blockColour = function(d){
    bird = goL.get(d);
    block = goL.getB(d);
    return block == 1 ? "red" : (bird == 1 ? "steelblue" : "white");
  }
  
  function switchSq(p){
    if(!editMode) return;
    goL.put(p,1-goL.get(p),i);
    rects.style("fill",function(d){ return goL.blockColour(d); });
  }
  
  goL.clearGrid();
  var rects = d3.select("svg").selectAll("rect").data(d3.range(0,bits)).enter().append("rect")
      .attr("x",function(d){ return (d&255)*5;})
      .attr("y",function(d){ return (d>>>8)*5;})
      .attr("width",5).attr("height",5)
      .style("fill",function(d){ return goL.blockColour(d); })
      .on("click",function(d){ return switchSq(d);});
  
  goL.setGrid = function(ar){  //set the initial bits
    goL.clearGrid();
    goL.clearTimeout();
    
    if(arguments.length > 0){
      d3.range(0,ar.length).forEach(function(y){d3.range(0,ar[0].length)
        .forEach(function(x){goL.put(y*256+x,ar[y][x],i)})});
    } 
    rects.style("fill",function(d){ return goL.blockColour(d); });
  }
  
  goL.update = function(){
    $.ajax({
      url: "step",
      async: false,
      success: function(res) {
        resjson = JSON.parse(res);
        resptr = 0;

        for(var p=0; p<bits; p++){
          if(resjson[resptr]['xy'] === p){
            disp = resjson[resptr]['disp'];
            if(disp===1){
              goL.put(p, 1, 1-i);    
            } else if(disp===2) {
              goL.putB(p, 1, 1-i);    
            }
            
            if(resptr+1 < resjson.length){
                resptr = resptr + 1;
            }
          } else {
            goL.put(p, 0, 1-i);
          }
        }
      }
    });

    i=1-i;// switch current
    rects.style("fill",function(d){ return goL.blockColour(d); });
    
    timeClr = setTimeout(function(){goL.update()},sp);
  }
  
  return goL;
}());