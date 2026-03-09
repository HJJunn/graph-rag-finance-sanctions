let network
let nodes
let edges

let allNodes=[]
let allEdges=[]

window.onload = async function(){

    await loadGraph()

}

async function loadGraph(){

    const res = await fetch("/graph")
    const data = await res.json()

    allNodes=data.nodes
    allEdges=data.edges

    nodes=new vis.DataSet(
        allNodes.map(n=>({

            id:n.id,
            label:n.label,
            title:n.title,
            shape:"dot",
            size:15

        }))
    )

    edges=new vis.DataSet(
        allEdges.map(e=>({

            id:e.id,
            from:e.source,
            to:e.target,
            arrows:"to"

        }))
    )

    const container=document.getElementById("network")

    network=new vis.Network(container,{
        nodes:nodes,
        edges:edges
    },{
        physics:true
    })

}

async function askQuestion(){

    const q=document.getElementById("question").value

    const res=await fetch("/query",{

        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            question:q
        })

    })

    const data=await res.json()

    document.getElementById("answer").innerHTML=
        marked.parse(data.answer)

    highlightGraph(data.used_nodes,data.used_edges)

}

function highlightGraph(nodeIds,edgeIds){

    nodes.forEach(n=>{

        nodes.update({

            id:n.id,
            color:"#DDD"

        })

    })

    nodeIds.forEach(id=>{

        nodes.update({

            id:id,
            color:"#FF6B6B",
            size:25

        })

    })

}