export default function FranchisorRequestsTableHeader() {
  return (
    <div className="rounded-sm bg-[#E25E3E]">
      <div className="flex text-white">
        <div className="w-[20%] px-6 py-3 text-xs font-black">Marca</div>
        <div className="w-[15%] px-6 py-3 text-xs text-center font-black">
          Tipo
        </div>
        <div className="w-[20%] px-6 py-3 text-xs text-center font-black">
          Franquia vinculada
        </div>
        <div className="w-[20%] px-6 py-3 text-xs text-center font-black">
          Usuário
        </div>
        <div className="w-[10%] px-6 py-3 text-xs text-center font-black">
          Status
        </div>
        <div className="w-[8%] px-6 py-3 text-xs text-center font-black">
          Data
        </div>
        <div className="w-[7%] px-6 py-3 text-xs text-center font-black">
          Ações
        </div>
      </div>
    </div>
  )
}
