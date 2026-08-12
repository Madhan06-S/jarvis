export type OrbState = "idle" | "listening" | "thinking" | "speaking";

export function createOrb(canvas: HTMLCanvasElement) {
  const wrap = document.getElementById('jarvis-wrap')!;
  const bg = document.getElementById('bgCanvas') as HTMLCanvasElement;
  const fg = document.getElementById('fgCanvas') as HTMLCanvasElement;
  const bctx = bg.getContext('2d')!;
  const fctx = fg.getContext('2d')!;

  let W = wrap.clientWidth, H = wrap.clientHeight;
  bg.width = fg.width = W;
  bg.height = fg.height = H;
  let cx = W/2, cy = H/2 - 30;

  const BLUE='#00BFFF', BLUE2='rgba(0,191,255,', CYAN='rgba(0,220,255,';

  let t = 0, startTime = Date.now();

  let state: OrbState = "idle";
  let analyser: AnalyserNode | null = null;
  const timeData = new Uint8Array(200);

  // Antigravity particles
  const PARTICLE_COUNT = 120;
  let particles: any[] = [];
  for(let i=0; i<PARTICLE_COUNT; i++){
    particles.push({
      x: Math.random()*W,
      y: Math.random()*H,
      vx: (Math.random()-0.5)*0.4,
      vy: -(Math.random()*0.6+0.1),
      size: Math.random()*2.2+0.3,
      alpha: Math.random()*0.7+0.2,
      pulse: Math.random()*Math.PI*2,
      connected: []
    });
  }

  // Floating holographic shards
  let shards: any[] = [];
  for(let i=0; i<18; i++){
    shards.push({
      x: Math.random()*W,
      y: Math.random()*H,
      vx: (Math.random()-0.5)*0.25,
      vy: -(Math.random()*0.3+0.05),
      w: Math.random()*40+15,
      h: Math.random()*8+3,
      rot: Math.random()*Math.PI,
      rotSpeed: (Math.random()-0.5)*0.015,
      alpha: Math.random()*0.25+0.05
    });
  }

  // Arc reactor rings config
  const rings = [
    {r:38, speed:0.018, dash:[6,4], w:1.2, phase:0},
    {r:55, speed:-0.013, dash:[3,7], w:0.8, phase:1},
    {r:72, speed:0.009, dash:[12,4,3,4], w:1.0, phase:2},
    {r:90, speed:-0.007, dash:[5,15], w:0.6, phase:3},
    {r:108, speed:0.005, dash:[20,6], w:0.8, phase:4},
    {r:130, speed:-0.004, dash:[4,30], w:0.5, phase:5},
    {r:155, speed:0.003, dash:[2,50], w:0.4, phase:6},
    {r:185, speed:-0.002, dash:[8,80], w:0.35, phase:7},
  ];

  // Hex grid nodes floating
  let hexNodes: any[] = [];
  for(let i=0; i<22; i++){
    let angle = Math.random()*Math.PI*2;
    let dist = 80+Math.random()*260;
    hexNodes.push({
      x: cx+Math.cos(angle)*dist,
      y: cy+Math.sin(angle)*dist,
      baseX: cx+Math.cos(angle)*dist,
      baseY: cy+Math.sin(angle)*dist,
      angle: Math.random()*Math.PI*2,
      speed: 0.008+Math.random()*0.012,
      amp: 4+Math.random()*12,
      size: 2+Math.random()*3,
      alpha: 0.3+Math.random()*0.5,
      pulse: Math.random()*Math.PI*2
    });
  }

  // DNA helix strands
  let dnaPoints: any[] = [];
  const dnaCount = 40;
  for(let i=0; i<dnaCount; i++){
    dnaPoints.push({t: i/dnaCount*Math.PI*4});
  }

  // Scan line
  let scanY = 0, scanDir = 1;

  function updateHUD() {
    const now = Date.now();
    const sec = Math.floor((now-startTime)/1000);
    const h = String(Math.floor(sec/3600)).padStart(2,'0');
    const m = String(Math.floor((sec%3600)/60)).padStart(2,'0');
    const s = String(sec%60).padStart(2,'0');
    const uEl = document.getElementById('uptime');
    if(uEl) uEl.textContent = h+':'+m+':'+s;
    const pCountEl = document.getElementById('p-count');
    if(pCountEl) pCountEl.textContent = String(PARTICLE_COUNT);
    // Fluctuating bars
    const cpu = 68 + Math.sin(t*0.7)*8;
    const mem = 55 + Math.cos(t*0.4)*6;
    const cpuBar = document.getElementById('cpu-bar');
    const cpuVal = document.getElementById('cpu-val');
    const memBar = document.getElementById('mem-bar');
    const memVal = document.getElementById('mem-val');
    if(cpuBar) cpuBar.style.width = cpu.toFixed(0)+'%';
    if(cpuVal) cpuVal.textContent = cpu.toFixed(0)+'%';
    if(memBar) memBar.style.width = mem.toFixed(0)+'%';
    if(memVal) memVal.textContent = mem.toFixed(0)+'%';
  }

  function drawArcReactor() {
    let speedMult = 1;
    let colorTint = 'rgba(150,240,255,0.95)';
    if(state === "listening") { speedMult = 2; colorTint = 'rgba(0,255,200,0.95)'; }
    if(state === "thinking") { speedMult = 4; colorTint = 'rgba(200,150,255,0.95)'; }
    if(state === "speaking") { speedMult = 1.5; colorTint = 'rgba(150,240,255,0.95)'; }

    // Core glow
    const grd = bctx.createRadialGradient(cx,cy,0,cx,cy,30);
    grd.addColorStop(0, colorTint);
    grd.addColorStop(0.3, 'rgba(0,180,255,0.6)');
    grd.addColorStop(0.7, 'rgba(0,100,200,0.2)');
    grd.addColorStop(1, 'rgba(0,0,0,0)');
    bctx.beginPath();
    bctx.arc(cx,cy,30,0,Math.PI*2);
    bctx.fillStyle = grd;
    bctx.fill();

    // Triangle in core
    bctx.save();
    bctx.translate(cx,cy);
    bctx.rotate(t*0.5*speedMult);
    bctx.beginPath();
    for(let i=0; i<3; i++){
      const a = i/3*Math.PI*2 - Math.PI/2;
      i===0 ? bctx.moveTo(Math.cos(a)*16,Math.sin(a)*16) : bctx.lineTo(Math.cos(a)*16,Math.sin(a)*16);
    }
    bctx.closePath();
    bctx.strokeStyle = `rgba(0,220,255,${0.7+Math.sin(t*2)*0.3})`;
    bctx.lineWidth = 1;
    bctx.stroke();
    bctx.restore();

    // Inner star
    bctx.save();
    bctx.translate(cx,cy);
    bctx.rotate(-t*0.8*speedMult);
    bctx.beginPath();
    for(let i=0; i<6; i++){
      const a = i/6*Math.PI*2;
      const r = i%2===0 ? 18 : 9;
      i===0 ? bctx.moveTo(Math.cos(a)*r,Math.sin(a)*r) : bctx.lineTo(Math.cos(a)*r,Math.sin(a)*r);
    }
    bctx.closePath();
    bctx.strokeStyle = 'rgba(0,200,255,0.5)';
    bctx.lineWidth = 0.5;
    bctx.stroke();
    bctx.restore();

    // Rotating rings
    rings.forEach((ring,i)=>{
      bctx.save();
      bctx.translate(cx,cy);
      bctx.rotate(t*ring.speed*speedMult + ring.phase);
      bctx.beginPath();
      bctx.arc(0,0,ring.r,0,Math.PI*2);
      bctx.setLineDash(ring.dash);
      const alpha = 0.35 + Math.sin(t*0.8 + ring.phase)*0.15;
      bctx.strokeStyle = `rgba(0,191,255,${alpha})`;
      bctx.lineWidth = ring.w;
      bctx.stroke();
      if(i%2===0){
        const ticks = 8 + i*2;
        for(let j=0; j<ticks; j++){
          const a = j/ticks*Math.PI*2;
          const r1 = ring.r-3, r2 = ring.r+3;
          bctx.beginPath();
          bctx.moveTo(Math.cos(a)*r1,Math.sin(a)*r1);
          bctx.lineTo(Math.cos(a)*r2,Math.sin(a)*r2);
          bctx.setLineDash([]);
          bctx.strokeStyle = `rgba(0,191,255,${alpha*0.6})`;
          bctx.lineWidth = 0.4;
          bctx.stroke();
        }
      }
      bctx.restore();
    });

    // Outer energy pulse ring
    const pR = 200 + Math.sin(t*1.5)*15;
    bctx.beginPath();
    bctx.arc(cx,cy,pR,0,Math.PI*2);
    bctx.strokeStyle = `rgba(0,191,255,${0.08+Math.sin(t*1.5)*0.04})`;
    bctx.setLineDash([]);
    bctx.lineWidth = 2;
    bctx.stroke();
  }

  function drawHexNodes(){
    bctx.setLineDash([2,4]);
    bctx.lineWidth=0.4;
    for(let i=0; i<hexNodes.length; i++){
      for(let j=i+1; j<hexNodes.length; j++){
        const dx = hexNodes[i].x-hexNodes[j].x;
        const dy = hexNodes[i].y-hexNodes[j].y;
        const dist = Math.sqrt(dx*dx+dy*dy);
        if(dist<120){
          const alpha = (1-dist/120)*0.3;
          bctx.beginPath();
          bctx.moveTo(hexNodes[i].x,hexNodes[i].y);
          bctx.lineTo(hexNodes[j].x,hexNodes[j].y);
          bctx.strokeStyle = `rgba(0,191,255,${alpha})`;
          bctx.stroke();
        }
      }
    }
    bctx.setLineDash([]);
    // Draw nodes
    hexNodes.forEach(n=>{
      n.angle += n.speed * (state === "thinking" ? 3 : 1);
      n.x = n.baseX + Math.sin(n.angle)*n.amp;
      n.y = n.baseY + Math.cos(n.angle*0.7)*n.amp*0.6;
      n.pulse += 0.04;
      const alpha = n.alpha*(0.7+Math.sin(n.pulse)*0.3);
      bctx.beginPath();
      for(let i=0; i<6; i++){
        const a = i/6*Math.PI*2 - Math.PI/6;
        const r = n.size;
        i===0 ? bctx.moveTo(n.x+Math.cos(a)*r, n.y+Math.sin(a)*r) : bctx.lineTo(n.x+Math.cos(a)*r, n.y+Math.sin(a)*r);
      }
      bctx.closePath();
      bctx.strokeStyle = `rgba(0,220,255,${alpha})`;
      bctx.lineWidth = 0.5;
      bctx.stroke();
      bctx.fillStyle = `rgba(0,150,220,${alpha*0.3})`;
      bctx.fill();
    });
  }

  function drawParticles(){
    particles.forEach(p=>{
      p.x += p.vx * (state === "thinking" ? 2 : 1);
      p.y += p.vy * (state === "thinking" ? 2 : 1);
      p.pulse += 0.05;
      // Antigravity pull
      const dx=cx-p.x, dy=cy-p.y;
      const dist = Math.sqrt(dx*dx+dy*dy);
      if(dist>200){ p.vx+=dx*0.00008; p.vy+=dy*0.00008; }
      if(p.y<-10) p.y=H+10;
      if(p.x<-10) p.x=W+10;
      if(p.x>W+10) p.x=-10;
    });

    fctx.lineWidth=0.4;
    for(let i=0; i<particles.length; i++){
      for(let j=i+1; j<particles.length; j++){
        const dx=particles[i].x-particles[j].x;
        const dy=particles[i].y-particles[j].y;
        const d=Math.sqrt(dx*dx+dy*dy);
        if(d<80){
          const a=(1-d/80)*0.25;
          fctx.beginPath();
          fctx.moveTo(particles[i].x,particles[i].y);
          fctx.lineTo(particles[j].x,particles[j].y);
          fctx.strokeStyle=`rgba(0,150,220,${a})`;
          fctx.stroke();
        }
      }
    }

    particles.forEach(p=>{
      const a = p.alpha*(0.6+Math.sin(p.pulse)*0.4);
      fctx.beginPath();
      fctx.arc(p.x, p.y, p.size, 0, Math.PI*2);
      fctx.fillStyle=`rgba(0,191,255,${a})`;
      fctx.fill();
      if(p.size>1.5){
        fctx.beginPath();
        fctx.arc(p.x, p.y, p.size+2, 0, Math.PI*2);
        fctx.strokeStyle=`rgba(0,191,255,${a*0.3})`;
        fctx.lineWidth=0.5;
        fctx.stroke();
      }
    });
  }

  function drawShards(){
    shards.forEach(s=>{
      s.x += s.vx; s.y += s.vy; s.rot += s.rotSpeed;
      if(s.y<-30) s.y=H+30;
      if(s.x<-60) s.x=W+60;
      if(s.x>W+60) s.x=-60;
      fctx.save();
      fctx.translate(s.x, s.y);
      fctx.rotate(s.rot);
      fctx.fillStyle=`rgba(0,191,255,${s.alpha})`;
      fctx.fillRect(-s.w/2, -s.h/2, s.w, s.h);
      fctx.restore();
    });
  }

  function drawDNA(){
    const dnaX=W-90, dnaY=cy-80, dnaH=160;
    fctx.lineWidth=0.8;
    for(let i=0; i<dnaCount-1; i++){
      const p1 = dnaPoints[i], p2 = dnaPoints[i+1];
      const y1 = dnaY + i/dnaCount*dnaH;
      const y2 = dnaY + (i+1)/dnaCount*dnaH;
      const x1a = dnaX + Math.sin(p1.t+t*0.8)*18;
      const x1b = dnaX - Math.sin(p1.t+t*0.8)*18;
      const x2a = dnaX + Math.sin(p2.t+t*0.8)*18;
      const x2b = dnaX - Math.sin(p2.t+t*0.8)*18;
      fctx.beginPath();
      fctx.moveTo(x1a,y1); fctx.lineTo(x2a,y2);
      fctx.strokeStyle='rgba(0,200,255,0.5)';
      fctx.stroke();
      fctx.beginPath();
      fctx.moveTo(x1b,y1); fctx.lineTo(x2b,y2);
      fctx.strokeStyle='rgba(0,140,220,0.4)';
      fctx.stroke();
      if(i%4===0){
        fctx.beginPath(); fctx.moveTo(x1a,y1); fctx.lineTo(x1b,y1);
        fctx.strokeStyle='rgba(0,191,255,0.6)'; fctx.stroke();
      }
    }
  }

  function drawScanLine(){
    scanY += scanDir*1.2;
    if(scanY>H) scanDir=-1;
    if(scanY<0) scanDir=1;
    const grd = fctx.createLinearGradient(0,scanY-6, 0,scanY+6);
    grd.addColorStop(0,'rgba(0,191,255,0)');
    grd.addColorStop(0.5,'rgba(0,191,255,0.06)');
    grd.addColorStop(1,'rgba(0,191,255,0)');
    fctx.fillStyle = grd;
    fctx.fillRect(0, scanY-6, W, 12);
  }

  function drawRadarArm(){
    bctx.save();
    bctx.translate(cx,cy);
    bctx.rotate(t*0.4 * (state==="listening"?2:1));
    bctx.beginPath();
    bctx.moveTo(0,0);
    bctx.arc(0,0,185,0,0.6);
    bctx.closePath();
    bctx.fillStyle='rgba(0,191,255,0.04)';
    bctx.fill();
    bctx.restore();
  }

  function drawEnergyBeams(){
    const beamAngles = [0, Math.PI*2/3, Math.PI*4/3];
    beamAngles.forEach((a,i)=>{
      const angle = a + t*0.3;
      const len = 70 + Math.sin(t*2+i)*20;
      const x2 = cx + Math.cos(angle)*len;
      const y2 = cy + Math.sin(angle)*len;
      const grd = bctx.createLinearGradient(cx,cy,x2,y2);
      grd.addColorStop(0, `rgba(0,220,255,${0.4+Math.sin(t*3+i)*0.2})`);
      grd.addColorStop(1, 'rgba(0,100,200,0)');
      bctx.beginPath();
      bctx.moveTo(cx,cy);
      bctx.lineTo(x2,y2);
      bctx.strokeStyle=grd;
      bctx.lineWidth=1.5;
      bctx.setLineDash([]);
      bctx.stroke();
    });
  }

  function drawMiniCharts(){
    const barW=140, barH=24, barX=cx-barW/2, barY=H-55;
    fctx.strokeStyle='rgba(0,191,255,0.3)';
    fctx.lineWidth=0.5;
    fctx.strokeRect(barX,barY,barW,barH);

    // waveform inside
    fctx.beginPath();
    if (analyser && state === "speaking") {
        analyser.getByteTimeDomainData(timeData);
        for(let i=0; i<barW; i++){
            const index = Math.floor((i/barW) * timeData.length);
            const v = timeData[index] / 128.0;
            const y = barY + barH/2 + Math.sin(i*0.2+t*3)*3 + v * 8;
            i===0 ? fctx.moveTo(barX+i,y) : fctx.lineTo(barX+i,y);
        }
    } else {
        for(let i=0; i<=barW; i++){
            const y = barY + barH/2 + Math.sin(i*0.2+t*3)*5 + Math.sin(i*0.05+t)*4;
            i===0 ? fctx.moveTo(barX+i,y) : fctx.lineTo(barX+i,y);
        }
    }
    fctx.strokeStyle = `rgba(0,200,255,${0.5+Math.sin(t*2)*0.2})`;
    fctx.lineWidth = 1;
    fctx.stroke();
  }

  function frame(){
    t += 0.016;
    bctx.clearRect(0,0,W,H);
    fctx.clearRect(0,0,W,H);

    const vgrd = bctx.createRadialGradient(cx,cy,100,cx,cy,W*0.7);
    vgrd.addColorStop(0,'rgba(0,10,30,0)');
    vgrd.addColorStop(1,'rgba(0,0,10,0.7)');
    bctx.fillStyle = vgrd;
    bctx.fillRect(0,0,W,H);

    drawHexNodes();
    drawArcReactor();
    drawRadarArm();
    drawEnergyBeams();
    drawParticles();
    drawShards();
    drawDNA();
    drawScanLine();
    drawMiniCharts();

    if(t%0.5<0.016) updateHUD();
    requestAnimationFrame(frame);
  }

  window.addEventListener('resize', ()=> {
    W = wrap.clientWidth; H = wrap.clientHeight;
    bg.width = fg.width = W;
    bg.height = fg.height = H;
    cx = W/2; cy = H/2 - 30;
  });

  frame();

  return {
    setState: (s: OrbState) => { state = s; },
    setAnalyser: (a: AnalyserNode) => { analyser = a; }
  };
}
