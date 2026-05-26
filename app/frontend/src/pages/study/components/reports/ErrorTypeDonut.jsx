import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import ChartContainer from './shared/ChartContainer';
const COLORS = ['#2563eb', '#b45309', '#b91c1c', '#64748b'];
export default function ErrorTypeDonut({ data = [], loading, error, dataTestId, height = 280 }) {return <ChartContainer title="Error Type Breakdown" summary="Classification split for selected attempt." loading={loading} error={error} isEmpty={!data.length} dataTestId={dataTestId} height={height}><ResponsiveContainer width="100%" height={height-40}><PieChart><Pie data={data} dataKey="value" nameKey="label" outerRadius={95}>{data.map((e, i)=><Cell key={e.label} fill={COLORS[i % COLORS.length]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer></ChartContainer>;}
