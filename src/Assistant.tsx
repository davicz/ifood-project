import { useEffect, useRef, useState } from 'react';
import { Sparkles, ArrowRight, Search } from 'lucide-react';
import { money, type Recipe, type Ingredient } from './data';

type Interpretation = { recipe_ids: string[]; servings: number | null; pantry_ids: string[]; sort: 'price' | 'time'; split: boolean; clarification: string };
type Proposal = { provider: string; model: string | null; interpretation: Interpretation };
type Match = { id: string; name: string; score: number; store_name?: string; stock?: number; pack?: number; unit?: string; price_cents?: number };
async function post<T>(path: string, body: unknown, signal: AbortSignal): Promise<T> {
  const response = await fetch(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body), signal});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : 'Revise o pedido e tente novamente.');
  return data;
}
export function Assistant({recipes, ingredients, apply}: {recipes: Recipe[]; ingredients: Ingredient[]; apply: (proposal: Interpretation) => void}) {
  const [text, setText] = useState('');
  const [provider, setProvider] = useState('local');
  const [target, setTarget] = useState('recipes');
  const [proposal, setProposal] = useState<Proposal | null>(null);
  const [results, setResults] = useState<Match[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [bedrock, setBedrock] = useState(false);
  const active = useRef<AbortController | null>(null);
  useEffect(() => {
    const c = new AbortController();
    fetch('/api/ai/status', {signal:c.signal}).then(r => r.json()).then(d => setBedrock(d.bedrock_configured)).catch(() => {});
    return () => { c.abort(); active.current?.abort(); };
  }, []);
  function reset() { active.current?.abort(); setProposal(null); setResults([]); setError(''); setBusy(false); }
  async function run(mode: 'interpret' | 'search') {
    if (!text.trim()) return;
    reset(); const controller = new AbortController(); active.current = controller; setBusy(true);
    try {
      if (mode === 'interpret') setProposal(await post<Proposal>('/api/interpret', {text:text.trim(), provider}, controller.signal));
      else { const data = await post<{results:Match[]}>('/api/search', {query:text.trim(), target, method:'semantic', limit:3}, controller.signal); setResults(data.results); }
    } catch (e) { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Não foi possível consultar.'); }
    finally { if (!controller.signal.aborted) setBusy(false); }
  }
  return <section className="assistant-panel" aria-labelledby="assistant-title"><div className="assistant-heading"><span className="idea-icon"><Sparkles size={25}/></span><div><h2 id="assistant-title">Sua próxima compra começa com uma ideia.</h2><p>Conte o que quer preparar ou encontre pratos e ingredientes por significado.</p></div></div><form onSubmit={e => {e.preventDefault(); void run('interpret');}}><label className="assistant-input">O que vamos preparar?<textarea value={text} onChange={e => {reset(); setText(e.target.value);}} maxLength={2000} placeholder="Quero estrogonofe para quatro pessoas" required rows={2}/></label><div className="assistant-actions"><label>Interpretação<select value={provider} onChange={e => {reset(); setProvider(e.target.value);}}><option value="local">Local · regras simples</option><option value="bedrock" disabled={!bedrock}>AWS Bedrock{!bedrock && ' · configurar acesso'}</option></select></label><button className="primary" disabled={busy || !text.trim()} type="submit">{busy ? 'Consultando…' : 'Interpretar pedido'}<ArrowRight size={16}/></button></div></form><div className="semantic-actions"><label>Buscar em<select value={target} onChange={e => {reset(); setTarget(e.target.value);}}><option value="recipes">Pratos</option><option value="products">Produtos dos mercados</option></select></label><button className="secondary" disabled={busy || text.trim().length < 2} onClick={() => void run('search')}><Search size={15}/> Buscar por significado</button></div><p className="assistant-note">{provider === 'local' ? 'O modo local reconhece nomes e porções por regras; não usa LLM. A busca por significado usa embeddings locais.' : 'Bedrock envia seu texto e o catálogo de receitas ao modelo configurado na AWS.'} Sempre revise antes de aplicar.</p>{error && <p className="assistant-error" role="alert">{error}</p>}{busy && <p role="status" className="assistant-note">Consultando. Na primeira busca, o modelo local pode levar alguns segundos para carregar.</p>}{proposal && <div className="proposal"><h3>Confira o que entendemos</h3><p><b>Pratos:</b> {proposal.interpretation.recipe_ids.map(id => recipes.find(r => r.id === id)?.name).join(', ') || 'Nenhum identificado'}</p><p><b>Pessoas:</b> {proposal.interpretation.servings ?? 'Não informado — manter sua escolha atual'}</p><p><b>Já tenho:</b> {proposal.interpretation.pantry_ids.map(id => ingredients.find(i => i.id === id)?.name).join(', ') || 'Nenhum ingrediente marcado'}</p><p><b>Prioridade:</b> {proposal.interpretation.sort === 'price' ? 'Menor preço' : 'Menor prazo'} · {proposal.interpretation.split ? 'Comparar divisão em duas lojas' : 'Uma loja'}</p><p><b>Modo:</b> {proposal.provider === 'bedrock' ? `LLM · ${proposal.model}` : 'Regras locais'}</p>{proposal.interpretation.clarification && <p className="assistant-error">{proposal.interpretation.clarification}</p>}<button className="primary" disabled={!proposal.interpretation.recipe_ids.length || !!proposal.interpretation.clarification} onClick={() => apply(proposal.interpretation)}>Confirmar pratos e revisar ingredientes <ArrowRight size={16}/></button><small>Substitui os pratos atuais. Você poderá revisar porções e despensa na próxima tela.</small></div>}{results.length > 0 && <div className="semantic-results"><p className="assistant-note">Sugestões por similaridade. Não garantem adequação à receita nem a restrições alimentares.</p>{results.map(result => <article key={result.id}><div><b>{result.name}</b><p>{result.store_name ? `${result.store_name} · ${result.pack} ${result.unit} · ${money((result.price_cents ?? 0) / 100)} · ${result.stock ? 'Disponível' : 'Sem estoque'}` : 'Receita do catálogo de demonstração'}</p></div>{!result.store_name && <button className="secondary" onClick={() => apply({recipe_ids:[result.id],servings:null,pantry_ids:[],sort:'price',split:false,clarification:''})}>Escolher prato</button>}</article>)}</div>}</section>;
}
