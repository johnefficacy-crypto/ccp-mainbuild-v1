import React from 'react';
import { QuestionPalette, SectionTimer, SubmitConfirmDialog, AntiCheatProvider, PaletteLegend } from './index';

export default { title: 'Study/Mock/ShellPrimitives' };
const questions = Array.from({ length: 100 }, (_, i) => ({ id: `q${i+1}`, index: i, section_id: i < 50 ? 'A' : 'B' }));
const statusMap = Object.fromEntries(questions.map((q, i) => [q.id, ['not_visited','visited','answered','marked','answered_marked'][i%5]]));

export const Palette = () => <><PaletteLegend /><QuestionPalette questions={questions} statusMap={statusMap} currentIndex={3} onJump={()=>{}} /></>;
export const Timers = () => <><SectionTimer expiresAt={new Date(Date.now()+10000).toISOString()} onExpire={()=>{}} /><SectionTimer expiresAt={new Date(Date.now()+60000).toISOString()} onExpire={()=>{}} /><SectionTimer expiresAt={new Date(Date.now()+3600000).toISOString()} onExpire={()=>{}} /></>;
export const ConfirmDialog = () => <SubmitConfirmDialog open summary={{total:100,answered:40,marked:10,not_visited:20,time_remaining_sec:120}} onConfirm={()=>{}} onCancel={()=>{}} />;
export const AntiCheat = () => <AntiCheatProvider enforceFullscreen blockCopy blockPaste onViolation={()=>{}}><div>Attempt area</div></AntiCheatProvider>;
