const $ = (selector) => document.querySelector(selector);
const hostnameEl = $("#hostname");
const timeEl = $("#time");
const uptimeEl = $("#uptime");
const loadEl = $("#load");
const cpuBarsEl = $("#cpu-bars");
const cpuMetaEl = $("#cpu-meta");
const ramBar = $("#ram-bar");
const ramText = $("#ram-text");
const swapBar = $("#swap-bar");
const swapText = $("#swap-text");
const diskEl = $("#disk");
const networkEl = $("#network");
const tempsEl = $("#temps");
const procsEl = $("#procs");
const restartBtn = $("#restart-btn");
const restartStatus = $("#restart-status");
const apiKeyInput = $("#api-key");

let pollTimer = null;

const formatBytes = (bytes) => {
	if (!Number.isFinite(bytes)) return "0 B";
	const units = ["B", "KB", "MB", "GB", "TB"];
	let idx = 0;
	let value = bytes;
	while (value >= 1024 && idx < units.length - 1) {
		value /= 1024;
		idx += 1;
	}
	return `${value.toFixed(1)} ${units[idx]}`;
};

const formatDuration = (seconds) => {
	const days = Math.floor(seconds / 86400);
	const hours = Math.floor((seconds % 86400) / 3600);
	const minutes = Math.floor((seconds % 3600) / 60);
	const parts = [];
	if (days) parts.push(`${days}d`);
	if (hours) parts.push(`${hours}h`);
	parts.push(`${minutes}m`);
	return parts.join(" ");
};

const renderCpu = (cpu) => {
	cpuBarsEl.innerHTML = "";
	cpu.per_core.forEach((value, index) => {
		const wrapper = document.createElement("div");
		wrapper.className = "bar";
		const label = document.createElement("span");
		label.textContent = `#${index}`;
		const bar = document.createElement("div");
		bar.style.height = `${Math.min(100, value)}%`;
		wrapper.append(label, bar);
		cpuBarsEl.appendChild(wrapper);
	});
	cpuMetaEl.textContent = `Usage: ${cpu.usage_percent.toFixed(1)}% | Cores: ${cpu.count} | Freq: ${cpu.frequency_mhz?.toFixed?.(0) ?? "n/a"} MHz`;
};

const renderMemory = (memory) => {
	const virtual = memory.virtual;
	const swap = memory.swap;
	const ramPercent = virtual.percent ?? (virtual.used / virtual.total) * 100;
	ramBar.style.width = `${ramPercent.toFixed(1)}%`;
	ramText.textContent = `${formatBytes(virtual.used)} / ${formatBytes(virtual.total)} (${ramPercent.toFixed(1)}%)`;

	const swapPercent = swap.total ? ((swap.used / swap.total) * 100) : 0;
	swapBar.style.width = `${swapPercent.toFixed(1)}%`;
	swapText.textContent = `${formatBytes(swap.used)} / ${formatBytes(swap.total)} (${swapPercent.toFixed(1)}%)`;
};

const renderDisk = (disks) => {
	const root = disks.root;
	if (!root) {
		diskEl.textContent = "No disk info";
		return;
	}
	const percent = ((root.used / root.total) * 100).toFixed(1);
	diskEl.textContent = `Root: ${formatBytes(root.used)} / ${formatBytes(root.total)} (${percent}%)`;
};

const renderNetwork = (net) => {
	if (!net || Object.keys(net).length === 0) {
		networkEl.textContent = "No network stats";
		return;
	}
	networkEl.textContent = `Sent ${formatBytes(net.bytes_sent)} | Recv ${formatBytes(net.bytes_recv)}`;
};

const renderTemps = (temps) => {
	tempsEl.innerHTML = "";
	if (!temps || temps.length === 0) {
		const li = document.createElement("li");
		li.textContent = "No temperature sensors";
		tempsEl.appendChild(li);
		return;
	}
	temps.forEach((sensor) => {
		const li = document.createElement("li");
		const limit = sensor.high ?? sensor.critical;
		const warning = limit ? ` / ${limit}°C` : "";
		li.textContent = `${sensor.sensor} ${sensor.label}: ${sensor.current}°C${warning}`;
		tempsEl.appendChild(li);
	});
};

const renderProcesses = (processes) => {
	procsEl.innerHTML = "";
	processes.forEach((proc) => {
		const tr = document.createElement("tr");
		tr.innerHTML = `<td>${proc.pid}</td><td>${proc.name}</td><td>${proc.username}</td><td>${proc.cpu_percent}</td><td>${proc.memory_percent}</td>`;
		procsEl.appendChild(tr);
	});
};

const updateUi = (payload) => {
	hostnameEl.textContent = `${payload.settings.hostname_label} / ${payload.hostname}`;
	timeEl.textContent = new Date(payload.timestamp).toLocaleString();
	uptimeEl.textContent = `Uptime ${formatDuration(payload.uptime_seconds)}`;
	loadEl.textContent = `Load ${payload.load_avg.map((v) => v.toFixed(2)).join(", ")}`;
	renderCpu(payload.cpu);
	renderMemory(payload.memory);
	renderDisk(payload.disks);
	renderNetwork(payload.network);
	renderTemps(payload.temperatures);
	renderProcesses(payload.top_processes);
};

const fetchMetrics = async () => {
	try {
		const res = await fetch("/api/metrics");
		if (!res.ok) throw new Error(`HTTP ${res.status}`);
		const payload = await res.json();
		updateUi(payload);
		const intervalMs = (payload.settings.poll_interval_seconds ?? 2) * 1000;
		if (!pollTimer) {
			pollTimer = setInterval(fetchMetrics, intervalMs);
		}
	} catch (error) {
		console.error("Failed to load metrics", error);
	}
};

const restartHandler = async () => {
	const token = apiKeyInput.value.trim();
	if (!token) {
		restartStatus.textContent = "API token required";
		restartStatus.style.color = "#f85149";
		return;
	}
	restartBtn.disabled = true;
	restartStatus.textContent = "Sending reboot command...";
	restartStatus.style.color = "#c9d1d9";
	try {
		const res = await fetch("/api/actions/restart", {
			method: "POST",
			headers: {
				"X-API-Key": token,
			},
		});
		if (!res.ok) {
			const data = await res.json().catch(() => ({}));
			throw new Error(data.detail || `HTTP ${res.status}`);
		}
		restartStatus.textContent = "Restart requested. The server may go offline shortly.";
		restartStatus.style.color = "#3fb950";
	} catch (error) {
		restartStatus.textContent = error.message;
		restartStatus.style.color = "#f85149";
	} finally {
		restartBtn.disabled = false;
	}
};

restartBtn.addEventListener("click", restartHandler);
fetchMetrics();
