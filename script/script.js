// Helpers -------------------------------------------------
function base() { return document.getElementById("base").value.trim() }
function key() { return document.getElementById("key").value.trim() }
async function api(path, opts = {}) {
  const r = await fetch(base() + path, {
    headers: Object.assign({ "x-api-key": key(), "Content-Type": "application/json" }, opts.headers || {}),
    method: opts.method || "GET",
    body: opts.body ? JSON.stringify(opts.body) : undefined
  });
  let data = null;
  try { data = await r.json() } catch (e) { }
  if (!r.ok) throw (data || { detail: r.statusText, status: r.status });
  return data;
}
function el(tag, attrs = {}, html = "") { const e = document.createElement(tag); Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v)); e.innerHTML = html; return e; }
function money(v) { return (v || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' }) }

// Ping ----------------------------------------------------
async function ping() {
  const span = document.getElementById("ping");
  span.textContent = "testando...";
  try { const d = await api("/status"); span.textContent = "OK • " + d.time; initLookups(); }
  catch (e) { span.textContent = "Falhou"; console.error(e) }
}

// Navegação -----------------------------------------------
function selectTab(node) {
  document.querySelectorAll("nav .item").forEach(i => i.classList.remove("active"));
  node.classList.add("active");
  const tab = node.getAttribute("data-tab");
  document.querySelectorAll("[id^='tab-']").forEach(d => d.style.display = "none");
  document.getElementById("tab-" + tab).style.display = "block";
  if (tab === "fornecedores") listarFornecedores();
  if (tab === "unidades") listarUnidades();
  if (tab === "produtos") { carregarFornecedoresSelect(); listarProdutos(); }
  if (tab === "limites") { carregarUnidadesSelect(); carregarProdutosSelect(); listarLimites(); }
  if (tab === "pedidos") { carregarUnidadesSelectPD(); carregarFornecedoresSelectPD(); setMesAno(); listarPedidos(); resetItens(); }
}

// Lookups -------------------------------------------------
async function initLookups() { carregarFornecedoresSelect(); carregarUnidadesSelect(); carregarProdutosSelect(); carregarFornecedoresSelectPD(); carregarUnidadesSelectPD(); }

async function carregarFornecedoresSelect() {
  const sel = document.getElementById("p-fornecedor");
  if (!sel) return;
  const fs = await api("/fornecedores");
  sel.innerHTML = fs.map(f => `<option value="${f.id}">${f.id} • ${f.codigo} - ${f.razao_social}</option>`).join("");
}
async function carregarUnidadesSelect() {
  const sel = document.getElementById("l-unidade");
  if (!sel) return;
  const us = await api("/unidades");
  sel.innerHTML = us.map(u => `<option value="${u.id}">${u.id} • ${u.codigo} - ${u.nome}</option>`).join("");
}
async function carregarProdutosSelect() {
  const sel = document.getElementById("l-produto");
  if (!sel) return;
  const ps = await api("/produtos");
  sel.innerHTML = ps.map(p => `<option value="${p.id}">${p.id} • ${p.codigo} - ${p.nome}</option>`).join("");
}

async function carregarFornecedoresSelectPD() {
  const sel = document.getElementById("pd-fornecedor");
  const fs = await api("/fornecedores");
  sel.innerHTML = fs.map(f => `<option value="${f.id}">${f.id} • ${f.codigo} - ${f.razao_social}</option>`).join("");
  carregarProdutosFornecedor();
}
async function carregarUnidadesSelectPD() {
  const sel = document.getElementById("pd-unidade");
  const us = await api("/unidades");
  sel.innerHTML = us.map(u => `<option value="${u.id}">${u.id} • ${u.codigo} - ${u.nome}</option>`).join("");
}
async function carregarProdutosFornecedor() {
  const fid = document.getElementById("pd-fornecedor").value;
  const ps = await api("/produtos?fornecedor_id=" + fid);
  const tbody = document.getElementById("itens-body");
  [...tbody.querySelectorAll("select[name='produto_id']")].forEach(sel => {
    sel.innerHTML = ps.map(p => `<option value="${p.id}" data-preco="${p.preco}">${p.codigo} - ${p.nome} (${money(p.preco)})</option>`).join("");
  });
}

// Fornecedores --------------------------------------------
async function criarFornecedor() {
  const body = { codigo: v("f-codigo"), razao_social: v("f-razao"), cnpj: v("f-cnpj") || null, email_pedidos: v("f-email") || null };
  await api("/fornecedores", { method: "POST", body }); limpar(["f-codigo", "f-razao", "f-cnpj", "f-email"]); listarFornecedores(); carregarFornecedoresSelect(); carregarFornecedoresSelectPD();
}
async function listarFornecedores() {
  const fs = await api("/fornecedores");
  const tb = document.getElementById("fornecedores-body");
  tb.innerHTML = fs.map(f => `<tr><td>${f.id}</td><td>${f.codigo}</td><td>${f.razao_social}</td><td>${f.email_pedidos || ""}</td><td class="actions"><button onclick="del('/fornecedores/${f.id}', listarFornecedores)">Excluir</button></td></tr>`).join("");
}

// Unidades ------------------------------------------------
async function criarUnidade() {
  const body = { codigo: v("u-codigo"), nome: v("u-nome"), cnpj: v("u-cnpj") || null, centro_custo: v("u-cc") || null, ativa: true };
  await api("/unidades", { method: "POST", body }); limpar(["u-codigo", "u-nome", "u-cnpj", "u-cc"]); listarUnidades(); carregarUnidadesSelect(); carregarUnidadesSelectPD();
}
async function listarUnidades() {
  const us = await api("/unidades");
  const tb = document.getElementById("unidades-body");
  tb.innerHTML = us.map(u => `<tr><td>${u.id}</td><td>${u.codigo}</td><td>${u.nome}</td><td>${u.cnpj || ""}</td><td class="actions"><button onclick="del('/unidades/${u.id}', listarUnidades)">Excluir</button></td></tr>`).join("");
}

// Produtos ------------------------------------------------
async function criarProduto() {
  const body = { codigo: v("p-codigo"), nome: v("p-nome"), unidade_medida: v("p-um") || "UN", fornecedor_id: parseInt(v("p-fornecedor")), preco: parseFloat(v("p-preco") || "0"), ativo: true };
  await api("/produtos", { method: "POST", body }); limpar(["p-codigo", "p-nome", "p-preco"]); listarProdutos(); carregarProdutosSelect(); carregarProdutosFornecedor();
}
async function listarProdutos() {
  const ps = await api("/produtos");
  const fs = await api("/fornecedores");
  const mapF = Object.fromEntries(fs.map(f => [f.id, f]));
  const tb = document.getElementById("produtos-body");
  tb.innerHTML = ps.map(p => `<tr><td>${p.id}</td><td>${p.codigo}</td><td>${p.nome}</td><td>${p.unidade_medida}</td><td>${money(p.preco)}</td><td>${mapF[p.fornecedor_id]?.razao_social || p.fornecedor_id}</td><td class="actions"><button onclick="del('/produtos/${p.id}', listarProdutos)">Excluir</button></td></tr>`).join("");
}

// Limites -------------------------------------------------
async function criarLimite() {
  const body = { unidade_id: parseInt(v("l-unidade")), produto_id: parseInt(v("l-produto")), minimo: parseFloat(v("l-min") || "0"), maximo: parseFloat(v("l-max") || "999999") };
  await api("/limites", { method: "POST", body }); limpar(["l-min", "l-max"]); listarLimites();
}
async function listarLimites() {
  const ls = await api("/limites");
  const us = await api("/unidades"); const mapU = Object.fromEntries(us.map(u => [u.id, u]));
  const ps = await api("/produtos"); const mapP = Object.fromEntries(ps.map(p => [p.id, p]));
  const tb = document.getElementById("limites-body");
  tb.innerHTML = ls.map(l => `<tr><td>${l.id}</td><td>${mapU[l.unidade_id]?.codigo || l.unidade_id}</td><td>${mapP[l.produto_id]?.codigo || l.produto_id}</td><td>${l.minimo}</td><td>${l.maximo}</td><td class="actions"><button onclick="del('/limites/${l.id}', listarLimites)">Excluir</button></td></tr>`).join("");
}

// Pedidos -------------------------------------------------
function resetItens() { document.getElementById("itens-body").innerHTML = ""; addItem(); }
function addItem() {
  const tr = el("tr", {}, `
    <td><select name="produto_id"></select></td>
    <td><input name="qtd" type="number" min="0" step="0.01" value="1"></td>
    <td><input name="preco" type="number" step="0.01" placeholder="(vazio = preço padrão)"></td>
    <td><button onclick="this.closest('tr').remove()">remover</button></td>`);
  document.getElementById("itens-body").appendChild(tr);
  carregarProdutosFornecedor();
}
async function criarPedido() {
  const itens = [...document.querySelectorAll("#itens-body tr")].map(tr => {
    const produto_id = parseInt(tr.querySelector("select[name='produto_id']").value);
    const quantidade = parseFloat(tr.querySelector("input[name='qtd']").value || "0");
    const precoStr = tr.querySelector("input[name='preco']").value.trim();
    return { produto_id, quantidade, preco: precoStr == "" ? null : parseFloat(precoStr) }
  }).filter(i => !isNaN(i.produto_id) && !isNaN(i.quantidade) && i.quantidade > 0);

  const body = {
    unidade_id: parseInt(v("pd-unidade")),
    fornecedor_id: parseInt(v("pd-fornecedor")),
    gerente_nome: v("pd-gerente"),
    contato: v("pd-contato") || null,
    desejado_para: v("pd-data") || null,
    observacoes: null,
    itens
  };
  try {
    const p = await api("/pedidos", { method: "POST", body });
    document.getElementById("pedido-out").textContent = "Pedido criado: #" + p.id + " | total " + money(p.valor_total) + " | status " + p.status + "\nClique em Enviar na tabela abaixo.";
    listarPedidos();
  } catch (e) { alert("Erro: " + (e.detail || JSON.stringify(e))); }
}
function setMesAno() {
  const d = new Date();
  document.getElementById("mes").value = d.getMonth() + 1;
  document.getElementById("ano").value = d.getFullYear();
}
async function listarPedidos() {
  const mes = parseInt(v("mes") || "");
  const ano = parseInt(v("ano") || "");
  const qs = (!isNaN(mes) && !isNaN(ano)) ? `?mes=${mes}&ano=${ano}` : "";
  const ps = await api("/pedidos" + qs);
  const us = await api("/unidades"); const mapU = Object.fromEntries(us.map(u => [u.id, u]));
  const fs = await api("/fornecedores"); const mapF = Object.fromEntries(fs.map(f => [f.id, f]));
  const tb = document.getElementById("pedidos-body");
  tb.innerHTML = ps.map(p => {
    const badge = p.status === "autorizado" ? "ok" : (p.status === "pendente_aprovacao" ? "warn" : "pill");
    return `<tr>
      <td>${p.id}</td>
      <td>${new Date(p.criado_em).toLocaleString('pt-BR')}</td>
      <td>${mapU[p.unidade_id]?.codigo || p.unidade_id}</td>
      <td>${mapF[p.fornecedor_id]?.codigo || p.fornecedor_id}</td>
      <td><span class="pill ${badge}">${p.status}</span></td>
      <td>${money(p.valor_total)}</td>
      <td class="actions">
        <button onclick="enviar(${p.id})">Enviar</button>
        <button onclick="aprovar(${p.id}, true)">Aprovar</button>
        <button onclick="aprovar(${p.id}, false)">Reprovar</button>
        <button onclick="receber(${p.id})">Receber</button>
        <button onclick="del('/pedidos/${p.id}', listarPedidos)">Excluir</button>
      </td>
    </tr>`
  }).join("");
}
async function enviar(id) { try { await api(`/pedidos/${id}/enviar`, { method: "POST" }); listarPedidos(); } catch (e) { alert("Erro: " + (e.detail || JSON.stringify(e))); } }
async function aprovar(id, ok) {
  try { await api(`/pedidos/${id}/aprovar`, { method: "POST", body: { decisor: "Matriz", aprovado: ok } }); listarPedidos(); }
  catch (e) { alert("Erro: " + (e.detail || JSON.stringify(e))); }
}
async function receber(id) {
  const hoje = new Date().toISOString().slice(0, 10);
  const qtd = prompt("Quantidade recebida:", "1");
  if (qtd === null) return;
  try { await api(`/pedidos/${id}/recebimentos`, { method: "POST", body: { data_recebimento: hoje, quantidade_recebida: parseFloat(qtd) } }); listarPedidos(); }
  catch (e) { alert("Erro: " + (e.detail || JSON.stringify(e))); }
}

// Utils ---------------------------------------------------
function v(id) { return document.getElementById(id).value }
function limpar(ids) { ids.forEach(id => document.getElementById(id).value = "") }
async function del(path, after) { if (!confirm("Tem certeza que deseja excluir?")) return; try { await api(path, { method: "DELETE" }); after && after(); } catch (e) { alert("Erro: " + (e.detail || JSON.stringify(e))); } }

// Start ---------------------------------------------------
// Adiciona um listener para garantir que o DOM está carregado antes de executar o script inicial.
document.addEventListener('DOMContentLoaded', (event) => {
    ping(); // tenta conectar ao abrir
});