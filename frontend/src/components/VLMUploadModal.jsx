import { useEffect, useState, useCallback } from "react"

// Backend returns one of: "No Damage" | "Minor Damage" | "Major Damage" | "Destroyed"
const DAMAGE_META = {
  "No Damage":    { score: 10, color: "#22c55e", dotClass: "bg-green-500"  },
  "Minor Damage": { score: 35, color: "#eab308", dotClass: "bg-yellow-500" },
  "Major Damage": { score: 70, color: "#fbb363", dotClass: "bg-orange-400" },
  "Destroyed":    { score: 95, color: "#ef4444", dotClass: "bg-red-500"    },
}

const MAX_FILE_MB = 20

// Intact house — Heroicons solid (home)
function BuildingIcon({ className }) {
  return (
    <svg
      className={className}
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 24 24"
      fill="currentColor"
    >
      <path d="M11.47 3.841a.75.75 0 0 1 1.06 0l8.69 8.69a.75.75 0 1 0 1.06-1.061l-8.689-8.69a2.25 2.25 0 0 0-3.182 0l-8.69 8.69a.75.75 0 1 0 1.061 1.06l8.69-8.689Z" />
      <path d="m12 5.432 8.159 8.159c.03.03.06.058.091.086v6.198c0 1.035-.84 1.875-1.875 1.875H15a.75.75 0 0 1-.75-.75v-4.5a.75.75 0 0 0-.75-.75h-3a.75.75 0 0 0-.75.75V21a.75.75 0 0 1-.75.75H5.625a1.875 1.875 0 0 1-1.875-1.875v-6.198a2.29 2.29 0 0 0 .091-.086L12 5.432Z" />
    </svg>
  )
}

// Broken / damaged house
function DamagedBuildingIcon({ className }) {
  return (
    <svg
      className={className}
      aria-hidden="true"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 380.076 380.076"
      fill="currentColor"
    >
      <path d="M376.104,162.526c0,0-33.497-25.689-33.497-25.798c0,0-2.796-2.722-2.796-8.222c0-14.081,0-56.324,0-56.324
        c0-6.341-5.159-11.5-11.5-11.5h-41.349c-6.341,0-11.5,5.159-11.5,11.5c0,0,0,7.087,0,9.449c0,2.625-1.431,1.419-1.431,1.419
        L197.8,23.694c-1.972-1.535-4.299-2.347-6.729-2.347c-3.981,0-7.634,2.245-9.533,5.858l-17.847,33.946
        c-2.173,4.133-2.181,9.91-0.02,14.047l23.054,44.152c0,0,1.688,2.279-0.606,6.314c-6.043,10.626-28.859,39.472-28.859,39.472
        c-2.781,3.803-3.599,9.551-1.989,13.979l6.123,16.839c0,0,1.977,5.384-1.841,2.244c-7.433-6.112-20.385-15.901-27.043-21.371
        c-3.639-2.989-0.818-6.591-0.818-6.591l22.764-39.832c2.665-4.667,2.066-11.019-1.423-15.105l-28.057-32.851
        c-2.213-2.591-5.458-4.078-8.902-4.078c-2.592,0-5.135,0.869-7.162,2.447L3.972,162.525c-4.076,3.172-4.502,7.292-3.541,10.089
        c0.96,2.797,3.826,5.787,8.991,5.787h23.115c0,0,2.366-0.229,2.366,2.188c0,41.66,0,166.641,0,166.641c0,6.341,5.159,11.5,11.5,11.5
        h102.623c6.341,0,11.5-5.159,11.5-11.5v-49.117c0-2.291-0.063-5.995-0.142-8.228c-0.004-0.151-0.305-15.278,8.602-24.426
        c4.747-4.877,11.257-7.247,19.901-7.247c9.171,0,16.402,2.592,21.493,7.704c9.173,9.212,9.218,23.985,9.218,24.102
        c-0.028,2.227-0.051,5.868-0.051,8.094v49.117c0,6.341,5.159,11.5,11.5,11.5h102.623c6.341,0,11.5-5.159,11.5-11.5
        c0,0,0-124.105,0-165.474c0-3.625,3.112-3.354,3.112-3.354h22.369c5.165,0,8.031-2.989,8.991-5.787
        C380.605,169.817,380.179,165.697,376.104,162.526z M290.463,77.755c0-2,1.998-2.074,1.998-2.074h29.748
        c0,0,2.603-0.092,2.603,2.658c0,9.938,0,29.148,0,39.75c0,4.417-2.538,2.521-2.538,2.521l-31.417-24.461
        c-0.148-0.193-0.394-0.581-0.394-1.956C290.463,94.193,290.463,82.152,290.463,77.755z M341.672,163.401
        c-6.341,0-11.5,5.159-11.5,11.5v165.104c0,0,0.491,3.724-3.634,3.724c-21.906,0-64.81,0-87.625,0c-4.375,0-4.364-4.099-4.364-4.099
        v-41.519c0-2.175,0.023-5.732,0.049-7.907c0.011-0.852,0.102-21.014-13.474-34.759c-8.018-8.118-18.864-12.234-32.235-12.234
        c-12.783,0-23.129,3.999-30.749,11.886c-13.327,13.795-12.775,34.405-12.745,35.277c0.072,2.083,0.133,5.626,0.133,7.737v42.769
        c0,0,0.261,2.849-4.364,2.849c-22.815,0-65.156,0-86.875,0c-5,0-4.384-4.099-4.384-4.099V174.901c0-6.341-5.159-11.5-11.5-11.5
        c0,0-5.649,0-7.533,0c-3,0-0.471-2.442-0.471-2.442l83.322-64.876c0,0,1.815-1.514,3.045-0.146
        c3.913,4.354,16.046,18.802,20.625,24.147c2.146,2.506-0.388,4.287-0.388,4.287l-64.308,41.233c-2.79,1.788-3.602,5.5-1.813,8.29
        c1.146,1.787,3.08,2.762,5.057,2.762c1.108,0,2.23-0.308,3.232-0.95c0,0,35.04-22.105,46.496-29.813
        c2.618-1.761,2.406,0.439,2.406,0.439l-12.983,22.718c-2.908,5.092-1.581,11.926,3.022,15.558l53.442,42.173
        c1.977,1.558,4.042,2.349,6.139,2.349h0.001c2.624,0,5.081-1.271,6.573-3.4c1.174-1.677,2.259-4.544,0.754-8.683l-15.571-42.82
        c0.003-0.131,0.028-0.31,0.063-0.436l31.383-42.923c2.962-4.053,3.425-10.223,1.102-14.672c0,0-8.027-15.621-10.838-20.755
        c-2.791-5.1,1.676-2.164,1.676-2.164l110.107,82.188c1.077,0.804,2.336,1.192,3.584,1.192c1.829,0,3.635-0.833,4.814-2.411
        c1.982-2.655,1.436-6.415-1.22-8.397L179.231,68.143c0,0-1.755-1.102-0.619-3.164c2.685-4.87,9.675-18.583,12.477-23.706
        c1.24-2.268,3.546-1.034,3.546-1.034l153.871,119.808c0,0,3.032,3.354-1.301,3.354C345.821,163.401,341.672,163.401,341.672,163.401
        z"/>
    </svg>
  )
}

function DropZone({ id, label, Icon, file, preview, onFile, onClear, disabled }) {
  const [dragOver, setDragOver] = useState(false)

  const handleFiles = (files) => {
    const f = files?.[0]
    if (!f) return
    if (!f.type.startsWith("image/")) {
      alert("Please upload an image file (PNG, JPG, etc.)")
      return
    }
    if (f.size > MAX_FILE_MB * 1024 * 1024) {
      alert(`File too large. Max ${MAX_FILE_MB}MB.`)
      return
    }
    onFile(f)
  }

  return (
    <div className="flex-1 min-w-0">
      <p className="text-white/60 text-xs font-semibold uppercase tracking-wide mb-2">{label}</p>

      {!file ? (
        <label
          htmlFor={id}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault()
            setDragOver(false)
            handleFiles(e.dataTransfer.files)
          }}
          className={`
            flex flex-col items-center justify-center w-full aspect-square
            border border-dashed rounded-xl cursor-pointer
            transition-colors duration-200
            ${dragOver
              ? "border-white/40 bg-white/10 text-white"
              : "border-white/10 bg-white/5 text-white/60 hover:bg-white/8 hover:text-white/90"}
            ${disabled ? "opacity-40 cursor-not-allowed pointer-events-none" : ""}
          `}
        >
          <div className="flex flex-col items-center justify-center pt-5 pb-6 px-4 text-center">
            <Icon className="w-9 h-9 mb-4" />
            <p className="mb-1 text-sm">
              <span className="font-semibold text-white/90">Click to upload</span>
            </p>
            <p className="text-xs text-white/40">or drag and drop</p>
            <p className="text-xs text-white/30 mt-2">PNG, JPG (max {MAX_FILE_MB}MB)</p>
          </div>
          <input
            id={id}
            type="file"
            accept="image/*"
            className="hidden"
            disabled={disabled}
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
      ) : (
        <div className="relative w-full aspect-square rounded-xl overflow-hidden border border-white/10 bg-white/5">
          <img src={preview} alt={label} className="w-full h-full object-cover" />
          <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/90 to-transparent px-3 py-2">
            <p className="text-white text-xs truncate">{file.name}</p>
          </div>
          {!disabled && (
            <button
              type="button"
              onClick={onClear}
              className="absolute top-2 right-2 w-7 h-7 flex items-center justify-center rounded-full bg-black/60 text-white/70 hover:text-white hover:bg-black/80 transition text-sm"
              aria-label={`Remove ${label}`}
            >
              ✕
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function Card({ label, children }) {
  return (
    <div className="p-4 rounded-xl border border-white/10 bg-white/5">
      <p className="text-white/60 text-xs font-semibold uppercase tracking-wide mb-2">{label}</p>
      {children}
    </div>
  )
}

export default function VLMUploadModal({ onClose }) {
  const [beforeFile, setBeforeFile] = useState(null)
  const [afterFile, setAfterFile] = useState(null)
  const [beforePreview, setBeforePreview] = useState(null)
  const [afterPreview, setAfterPreview] = useState(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!beforeFile) { setBeforePreview(null); return }
    const url = URL.createObjectURL(beforeFile)
    setBeforePreview(url)
    return () => URL.revokeObjectURL(url)
  }, [beforeFile])

  useEffect(() => {
    if (!afterFile) { setAfterPreview(null); return }
    const url = URL.createObjectURL(afterFile)
    setAfterPreview(url)
    return () => URL.revokeObjectURL(url)
  }, [afterFile])

  useEffect(() => {
    const handleKey = (e) => { if (e.key === "Escape" && !isSubmitting) onClose() }
    window.addEventListener("keydown", handleKey)
    return () => window.removeEventListener("keydown", handleKey)
  }, [onClose, isSubmitting])

  const canSubmit = beforeFile && afterFile && !isSubmitting

  const handleSubmit = useCallback(async () => {
    if (!canSubmit) return
    setIsSubmitting(true)
    setError(null)

    try {
      const formData = new FormData()
      formData.append("before", beforeFile)
      formData.append("after", afterFile)

      const response = await fetch("/api/assess", {
        method: "POST",
        body: formData,
      })

      if (!response.ok) throw new Error(`Server returned ${response.status}`)

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err?.message || "Something went wrong")
    } finally {
      setIsSubmitting(false)
    }
  }, [canSubmit, beforeFile, afterFile])

  const handleReset = () => {
    setBeforeFile(null)
    setAfterFile(null)
    setResult(null)
    setError(null)
  }

  const meta = result ? DAMAGE_META[result.damage_level] : null
  const score = meta?.score ?? 0

  return (
    <div
      className="fixed inset-0 z-[20000] flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm"
      onClick={() => !isSubmitting && onClose()}
    >
      <aside
        onClick={(e) => e.stopPropagation()}
        style={{ backgroundColor: "#1e1e1e" }}
        className="
          relative w-full max-w-2xl max-h-[90vh]
          border border-white/10 rounded-2xl shadow-2xl
          flex flex-col
          overflow-hidden
        "
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 shrink-0">
          <div>
            <h2 className="text-base font-semibold text-white">Damage Assessment</h2>
            <p className="text-white/40 text-xs mt-0.5">Upload pre & post imagery to evaluate damage</p>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="text-white/50 hover:text-white transition text-lg leading-none disabled:opacity-30 disabled:cursor-not-allowed"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {/* Divider */}
        <div className="h-px bg-white/10 shrink-0 mx-4" />

        {/* Body */}
        <div
          className="flex-1 overflow-y-auto min-h-0 px-5 py-4"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {!result ? (
            <>
              <div className="flex gap-4">
                <DropZone
                  id="dropzone-before"
                  label="Before"
                  Icon={BuildingIcon}
                  file={beforeFile}
                  preview={beforePreview}
                  onFile={setBeforeFile}
                  onClear={() => setBeforeFile(null)}
                  disabled={isSubmitting}
                />
                <DropZone
                  id="dropzone-after"
                  label="After"
                  Icon={DamagedBuildingIcon}
                  file={afterFile}
                  preview={afterPreview}
                  onFile={setAfterFile}
                  onClear={() => setAfterFile(null)}
                  disabled={isSubmitting}
                />
              </div>

              {error && (
                <div className="mt-4 px-4 py-3 rounded-xl border border-red-500/20 bg-red-500/10 text-red-300 text-sm">
                  {error}
                </div>
              )}

              {isSubmitting && (
                <div className="mt-6 flex flex-col items-center justify-center gap-3 py-4">
                  <div className="animate-spin w-5 h-5 border-2 border-white/20 border-t-white/70 rounded-full" />
                  <p className="text-white/60 text-sm">Analyzing imagery…</p>
                  <p className="text-white/30 text-xs">This may take 15–30 seconds</p>
                </div>
              )}
            </>
          ) : (
            /* Results */
            <div className="space-y-3">
              {/* Damage level card */}
              <div className="p-4 rounded-xl border border-white/10 bg-white/5">
                <div className="flex items-center justify-between mb-3">
                  <p className="text-white/60 text-xs font-semibold uppercase tracking-wide">Damage Level</p>
                  {typeof result.confidence === "number" && (
                    <p className="text-white/40 text-xs">Confidence {result.confidence}/10</p>
                  )}
                </div>
                <div className="flex items-center gap-3 mb-3">
                  <span className={`w-2.5 h-2.5 rounded-full ${meta.dotClass}`} />
                  <span className="text-xl font-semibold text-white">{result.damage_level}</span>
                  <span className="text-white/40 text-sm ml-auto">{score}/100</span>
                </div>
                <div className="h-1.5 w-full rounded-full bg-white/5 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-700"
                    style={{ width: `${score}%`, backgroundColor: meta.color }}
                  />
                </div>
                <div className="flex justify-between mt-1.5 text-[10px] text-white/30">
                  <span>None</span><span>Minor</span><span>Major</span><span>Destroyed</span>
                </div>
              </div>

              {/* Cost */}
              {result.cost_estimate_usd != null && (
                <Card label="Estimated Repair Cost">
                  <p className="text-white text-xl font-semibold">
                    ${Number(result.cost_estimate_usd).toLocaleString()}
                  </p>
                  {result.cost_reasoning && (
                    <p className="text-white/60 text-xs mt-2 leading-relaxed">{result.cost_reasoning}</p>
                  )}
                </Card>
              )}

              {result.building_description && (
                <Card label="Building (Pre-Disaster)">
                  <p className="text-white/90 text-sm leading-relaxed">{result.building_description}</p>
                </Card>
              )}
              {result.change_analysis && (
                <Card label="Observed Changes">
                  <p className="text-white/90 text-sm leading-relaxed">{result.change_analysis}</p>
                </Card>
              )}
              {result.damage_assessment && (
                <Card label="Assessment">
                  <p className="text-white/90 text-sm leading-relaxed">{result.damage_assessment}</p>
                </Card>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 px-5 py-4 flex items-center justify-end gap-3">
          {result ? (
            <>
              <button
                onClick={handleReset}
                className="text-white/50 hover:text-white transition text-sm"
              >
                New Assessment
              </button>
              <button
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm transition"
              >
                Done
              </button>
            </>
          ) : (
            <>
              <button
                onClick={onClose}
                disabled={isSubmitting}
                className="text-white/50 hover:text-white transition text-sm disabled:opacity-30 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleSubmit}
                disabled={!canSubmit}
                className="px-4 py-2 rounded-xl bg-white/10 hover:bg-white/20 text-white text-sm transition disabled:opacity-30 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSubmitting ? (
                  <>
                    <span className="animate-spin w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full" />
                    Analyzing…
                  </>
                ) : (
                  "Evaluate Damage"
                )}
              </button>
            </>
          )}
        </div>
      </aside>
    </div>
  )
}