import React from 'react';
const ITEMS = ['not_visited', 'visited', 'answered', 'marked', 'answered_marked'];
export default function PaletteLegend() { return <ul aria-label="Palette legend">{ITEMS.map((i)=><li key={i}><span style={{display:'inline-block',width:12,height:12,background:`var(--shell-status-${i})`,marginRight:8}} />{i.replace('_',' ')}</li>)}</ul>; }
