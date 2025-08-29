function addItem() {
    const tb = document.querySelector("#itens tbody");
    const tr = document.createElement("tr");
    tr.innerHTML = `
        <td><input placeholder="produto_id"></td>
        <td><input placeholder="qtd" type="number"></td>
        <td><input placeholder="preco (opcional)" type="number" step="0.01"></td>
        <td><button onclick="this.closest('tr').remove()">remover</button></td>
    `;
    tb.appendChild(tr);
}

async function enviar() {
    const out = document.getElementById("out");
    out.textContent = "Enviando..."; // Feedback para o usuário

    const base = document.getElementById("api").value.trim();
    const key = document.getElementById("key").value.trim();
    const unidade_id = parseInt(document.getElementById("unidade_id").value);
    const fornecedor_id = parseInt(document.getElementById("fornecedor_id").value);
    const gerente = document.getElementById("gerente").value.trim();
    const contato = document.getElementById("contato").value.trim();
    const desejado = document.getElementById("desejado").value.trim() || null;
    const obs = document.getElementById("obs").value.trim() || null;

    const itens = [...document.querySelectorAll("#itens tbody tr")].map(tr => {
        const tds = tr.querySelectorAll("td input");
        const pid = parseInt(tds[0].value);
        const qtd = parseFloat(tds[1].value);
        const preco = tds[2].value.trim();
        return {
            produto_id: pid,
            quantidade: qtd,
            preco: preco === '' ? null : parseFloat(preco)
        };
    }).filter(i => !isNaN(i.produto_id) && !isNaN(i.quantidade) && i.quantidade > 0);

    // Validação simples
    if (isNaN(unidade_id) || isNaN(fornecedor_id) || !gerente || itens.length === 0) {
        out.textContent = "Erro: Verifique se os IDs da unidade/fornecedor, o nome do gerente e pelo menos um item foram preenchidos corretamente.";
        return;
    }

    const body = {
        unidade_id,
        fornecedor_id,
        gerente_nome: gerente,
        contato,
        desejado_para: desejado,
        observacoes: obs,
        itens
    };

    try {
        const r = await fetch(`${base}/pedidos`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "x-api-key": key
            },
            body: JSON.stringify(body)
        });
        const data = await r.json();
        if (!r.ok) throw data;

        out.textContent = "Pedido criado com sucesso!\n\n" + JSON.stringify(data, null, 2) + "\n\nAgora clique abaixo para ENVIAR o pedido:";
        
        // Cria o botão para enviar
        const btn = document.createElement("button");
        btn.textContent = `Enviar pedido #${data.id} para aprovação/autorizar`;
        btn.style.marginTop = "12px";
        btn.onclick = async () => {
            btn.textContent = "Enviando...";
            btn.disabled = true;
            try {
                const r2 = await fetch(`${base}/pedidos/${data.id}/enviar`, {
                    method: "POST",
                    headers: { "x-api-key": key }
                });
                const d2 = await r2.json();
                if(!r2.ok) throw d2;
                out.textContent = "Pedido enviado com sucesso!\n\n" + JSON.stringify(d2, null, 2);
            } catch (e2) {
                out.textContent += "\n\nErro ao enviar o pedido:\n" + JSON.stringify(e2, null, 2);
            }
        };
        out.appendChild(btn);

    } catch (e) {
        out.textContent = "Erro na criação do pedido:\n" + JSON.stringify(e, null, 2);
    }
}

// Adiciona uma linha de item inicial quando a página carrega
document.addEventListener('DOMContentLoaded', addItem);