let network
let nodes
let edges

let allNodes = []
let allEdges = []

const USER_ID = "test_user"

window.onload = async function () {
    await loadGraph()
}

async function loadGraph() {
    const res = await fetch("/graph")
    const data = await res.json()

    allNodes = data.nodes
    allEdges = data.edges

    nodes = new vis.DataSet(
        allNodes.map(n => ({
            id: n.id,
            label: n.title ? String(n.title).substring(0, 20) : n.label,
            title: n.title,
            shape: "dot",
            size: 15,
            color: "#DDD"
        }))
    )

    edges = new vis.DataSet(
        allEdges.map(e => ({
            id: e.id,
            from: e.source,
            to: e.target,
            arrows: "to",
            color: "#CCC"
        }))
    )

    const container = document.getElementById("network")

    network = new vis.Network(
        container,
        { nodes: nodes, edges: edges },
        { physics: true }
    )
}

async function askQuestion() {
    const q = document.getElementById("question").value.trim()

    if (!q) {
        alert("질문을 입력해주세요.")
        return
    }

    const button = document.getElementById("askButton")
    if (button) button.disabled = true

    try {
        const res = await fetch("/query", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                user_id: USER_ID,
                question: q
            })
        })

        if (!res.ok) {
            const errorText = await res.text()
            console.error("Query API error:", res.status, errorText)
            alert(`질문 처리 실패: ${res.status}`)
            return
        }

        const data = await res.json()

        document.getElementById("answer").innerHTML =
            marked.parse(data.answer || "")

        highlightGraph(data.used_nodes || [], data.used_edges || [])

    } catch (err) {
        console.error(err)
        alert("서버 요청 중 오류가 발생했습니다.")
    } finally {
        if (button) button.disabled = false
    }
}

function highlightGraph(nodeIds, edgeIds) {
    if (!nodes || !edges) return

    nodes.forEach(n => {
        nodes.update({
            id: n.id,
            color: "#DDD",
            size: 15
        })
    })

    edges.forEach(e => {
        edges.update({
            id: e.id,
            color: "#CCC",
            width: 1
        })
    })

    nodeIds.forEach(id => {
        nodes.update({
            id: id,
            color: "#FF6B6B",
            size: 25
        })
    })

    edgeIds.forEach(id => {
        edges.update({
            id: id,
            color: "#FF6B6B",
            width: 3
        })
    })

    if (nodeIds.length > 0 && network) {
        network.fit({
            nodes: nodeIds,
            animation: true
        })
    }
}