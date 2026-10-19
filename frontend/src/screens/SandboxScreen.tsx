import React, { useCallback, useEffect, useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
  useWindowDimensions,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import Slider from "@react-native-community/slider";
import { LineChart } from "react-native-chart-kit";

const API_BASE_URL = (process.env.EXPO_PUBLIC_API_URL ?? "").replace(/\/$/, "");

type CropCatalogItem = {
  id: number;
  crop_name: string;
  hybrid_code: string;
  base_yield_kg_per_acre: number;
  min_temp_c: number;
  max_temp_c: number;
  heat_resilience_factor: number;
  drought_resilience_factor: number;
  disease_resistance_factor: number;
  pest_resistance_factor: number;
};

type SimulationResult = {
  crop_name: string;
  final_yield_kg_per_acre: number;
  calculated_loss_percentage: number;
  dominant_risk_factor: "Climate" | "Biological" | "Quality" | "Optimal";
  simulation_run_id: number;
  daily_health_history: DailyHealthPoint[];
  temp_slider_shift: number;
  water_slider_pct: number;
  weather_summary: WeatherSummary | null;
};

type DailyHealthPoint = {
  lifecycle_day: number;
  milestone: "Sowing" | "Vegetative" | "Flowering" | "Maturity" | string;
  health_percentage: number;
};

type WeatherSummary = {
  latitude: number;
  longitude: number;
  average_max_temperature_c: number;
  total_precipitation_mm: number;
  days_included: number;
  daily_dates: string[];
};

type SyncedCoordinates = { latitude: number; longitude: number };

type SliderControlProps = {
  title: string;
  value: number;
  minimumValue: number;
  maximumValue: number;
  step: number;
  unit: string;
  onValueChange: (value: number) => void;
};

function SliderControl({ title, value, minimumValue, maximumValue, step, unit, onValueChange }: SliderControlProps) {
  const displayValue = Number.isInteger(value) ? String(value) : value.toFixed(1);
  return (
    <View style={styles.control}>
      <View style={styles.controlHeader}>
        <Text style={styles.controlTitle}>{title}</Text>
        <Text style={styles.controlValue}>{displayValue}{unit}</Text>
      </View>
      <Slider minimumValue={minimumValue} maximumValue={maximumValue} step={step} value={value} onValueChange={onValueChange} minimumTrackTintColor="#287A55" maximumTrackTintColor="#D6E3D9" thumbTintColor="#287A55" accessibilityLabel={title} style={styles.slider} />
      <View style={styles.rangeLabels}>
        <Text style={styles.rangeText}>{minimumValue}{unit}</Text>
        <Text style={styles.rangeText}>{maximumValue > 0 ? "+" : ""}{maximumValue}{unit}</Text>
      </View>
    </View>
  );
}

function resiliencePercent(value: number): string {
  return `${(value * 100).toFixed(0)}%`;
}

export default function SandboxScreen() {
  const [cropCatalog, setCropCatalog] = useState<CropCatalogItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedCrop, setSelectedCrop] = useState("");
  const [tempShift, setTempShift] = useState(0);
  const [waterAdjust, setWaterAdjust] = useState(0);
  const [pestPressure, setPestPressure] = useState(0);
  const [diseasePressure, setDiseasePressure] = useState(0);
  const [germinationRate, setGerminationRate] = useState(95);
  const [simulationResult, setSimulationResult] = useState<SimulationResult | null>(null);
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [catalogError, setCatalogError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [latitudeInput, setLatitudeInput] = useState("");
  const [longitudeInput, setLongitudeInput] = useState("");
  const [syncedCoordinates, setSyncedCoordinates] = useState<SyncedCoordinates | null>(null);
  const [weatherSyncLoading, setWeatherSyncLoading] = useState(false);
  const { width: windowWidth } = useWindowDimensions();

  useEffect(() => {
    const controller = new AbortController();

    async function fetchAvailableCrops() {
      setIsLoading(true);
      setCatalogError(null);
      if (!API_BASE_URL) {
        setCatalogError("Set EXPO_PUBLIC_API_URL to the reachable FastAPI server URL.");
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/crops`, {
          headers: { Accept: "application/json" },
          signal: controller.signal,
        });
        if (!response.ok) {
          throw new Error(`Crop catalog request failed (${response.status}): ${await response.text()}`);
        }

        const catalog: CropCatalogItem[] = await response.json();
        if (!Array.isArray(catalog) || catalog.some((crop) =>
          typeof crop.crop_name !== "string" || typeof crop.hybrid_code !== "string"
        )) {
          throw new Error("The API returned an invalid crop catalog.");
        }

        if (!controller.signal.aborted) {
          setCropCatalog(catalog);
          setSelectedCrop((current) =>
            catalog.some((crop) => crop.crop_name === current)
              ? current
              : (catalog[0]?.crop_name ?? "")
          );
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setCatalogError(err instanceof Error ? err.message : "Unable to load crop catalog.");
        }
      } finally {
        if (!controller.signal.aborted) setIsLoading(false);
      }
    }

    void fetchAvailableCrops();
    return () => controller.abort();
  }, []);

  const fetchSimulationData = useCallback(async (signal: AbortSignal) => {
    if (!API_BASE_URL) {
      setError("Set EXPO_PUBLIC_API_URL to the reachable FastAPI server URL.");
      setSimulationLoading(false);
      setWeatherSyncLoading(false);
      return;
    }
    if (!selectedCrop || !cropCatalog.some((crop) => crop.crop_name === selectedCrop)) {
      setWeatherSyncLoading(false);
      return;
    }

    setSimulationLoading(true);
    setError(null);
    try {
      const activeCrop = cropCatalog.find((crop) => crop.crop_name === selectedCrop);
      if (!activeCrop) throw new Error("The selected crop is no longer in the catalog.");

      const weatherQuery = syncedCoordinates
        ? `?lat=${encodeURIComponent(String(syncedCoordinates.latitude))}&lon=${encodeURIComponent(String(syncedCoordinates.longitude))}`
        : "";
      const response = await fetch(`${API_BASE_URL}/api/v1/simulate-twin${weatherQuery}`, {
        method: "POST",
        headers: { Accept: "application/json", "Content-Type": "application/json" },
        body: JSON.stringify({
          crop_name: activeCrop.crop_name,
          temp_slider_shift: tempShift,
          water_slider_pct: waterAdjust,
          pest_pressure_pct: pestPressure,
          disease_pressure_pct: diseasePressure,
          base_germination_rate: germinationRate,
        }),
        signal,
      });

      if (!response.ok) {
        throw new Error(`Simulation API error (${response.status}): ${await response.text()}`);
      }

      const result: SimulationResult = await response.json();
      if (
        typeof result.final_yield_kg_per_acre !== "number" ||
        typeof result.calculated_loss_percentage !== "number" ||
        !["Climate", "Biological", "Quality", "Optimal"].includes(result.dominant_risk_factor) ||
        !Array.isArray(result.daily_health_history) ||
        typeof result.temp_slider_shift !== "number" ||
        typeof result.water_slider_pct !== "number"
      ) {
        throw new Error("The API returned an invalid simulation result.");
      }
      if (!signal.aborted) {
        setSimulationResult(result);
        if (result.weather_summary) {
          setTempShift(result.temp_slider_shift);
          setWaterAdjust(result.water_slider_pct);
          setWeatherSyncLoading(false);
        }
      }
    } catch (err) {
      if (!signal.aborted) {
        setError(err instanceof Error ? err.message : "Unable to retrieve simulation results.");
        setWeatherSyncLoading(false);
      }
    } finally {
      if (!signal.aborted) setSimulationLoading(false);
    }
  }, [cropCatalog, selectedCrop, tempShift, waterAdjust, pestPressure, diseasePressure, germinationRate, syncedCoordinates]);

  useEffect(() => {
    if (isLoading || !selectedCrop || catalogError) return;
    const controller = new AbortController();
    const timer = setTimeout(() => void fetchSimulationData(controller.signal), 300);
    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [fetchSimulationData, refreshKey, isLoading, selectedCrop, catalogError]);

  const syncLocalFieldWeather = () => {
    const latitude = Number(latitudeInput.trim());
    const longitude = Number(longitudeInput.trim());
    if (!latitudeInput.trim() || !longitudeInput.trim() || !Number.isFinite(latitude) || !Number.isFinite(longitude) || latitude < -90 || latitude > 90 || longitude < -180 || longitude > 180) {
      setError("Enter a valid latitude (-90 to 90) and longitude (-180 to 180).");
      return;
    }
    setError(null);
    setWeatherSyncLoading(true);
    setSyncedCoordinates({ latitude, longitude });
    setRefreshKey((value) => value + 1);
  };

  const resetSimulation = () => {
    if (cropCatalog.length > 0) setSelectedCrop(cropCatalog[0].crop_name);
    setTempShift(0);
    setWaterAdjust(0);
    setPestPressure(0);
    setDiseasePressure(0);
    setGerminationRate(95);
    setSyncedCoordinates(null);
    setWeatherSyncLoading(false);
  };

  const activeCrop = cropCatalog.find((crop) => crop.crop_name === selectedCrop);
  const finalHealthIndex = simulationResult ? Math.max(0, Math.min(100, 100 - simulationResult.calculated_loss_percentage)) : null;
  const chartColor = finalHealthIndex === null ? "#287A55" : finalHealthIndex > 80 ? "#20A464" : finalHealthIndex >= 50 ? "#E58A20" : "#D64545";
  const chartRgb = chartColor === "#20A464" ? "32,164,100" : chartColor === "#E58A20" ? "229,138,32" : chartColor === "#D64545" ? "214,69,69" : "40,122,85";
  const chartWidth = Math.max(280, windowWidth - 64);
  const riskColor = simulationResult?.dominant_risk_factor === "Optimal"
    ? "#287A55"
    : simulationResult?.dominant_risk_factor === "Quality"
      ? "#9B6A18"
      : simulationResult?.dominant_risk_factor === "Biological"
        ? "#B54747"
        : "#4767A8";

  return (
    <SafeAreaView style={styles.safeArea}>
      <ScrollView contentContainerStyle={styles.container} keyboardShouldPersistTaps="handled">
        <View style={styles.header}>
          <Text style={styles.eyebrow}>SEED INDUSTRY DIGITAL TWIN</Text>
          <Text style={styles.title}>SeedTwin AI</Text>
          <Text style={styles.subtitle}>Micro-Climate Simulation Sandbox</Text>
        </View>

        <View style={styles.metricsCard}>
          <Text style={styles.metricLabel}>SIMULATED FINAL YIELD</Text>
          <View style={styles.yieldRow}>
            <Text style={styles.yieldValue}>{simulationResult ? simulationResult.final_yield_kg_per_acre.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }) : "—"}</Text>
            <Text style={styles.yieldUnit}>kg/acre</Text>
          </View>
          <View style={styles.metricsFooter}>
            <View>
              <Text style={styles.smallLabel}>Dominant risk</Text>
              <Text style={[styles.riskValue, { color: riskColor }]}>{simulationResult?.dominant_risk_factor ?? "Awaiting data"}</Text>
            </View>
            <View style={styles.lossBlock}>
              <Text style={styles.smallLabel}>Calculated loss</Text>
              <Text style={styles.lossValue}>{simulationResult ? `${simulationResult.calculated_loss_percentage.toFixed(2)}%` : "—"}</Text>
            </View>
          </View>
          {simulationLoading && <View style={styles.loadingRow}><ActivityIndicator color="#287A55" size="small" /><Text style={styles.loadingText}>Updating simulation...</Text></View>}
          {(catalogError || error) && (
            <View style={styles.errorBox}>
              <Text style={styles.errorText}>{catalogError ?? error}</Text>
              {!catalogError && <Pressable onPress={() => setRefreshKey((value) => value + 1)} style={styles.retryButton}><Text style={styles.retryText}>Retry simulation</Text></Pressable>}
            </View>
          )}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Lifecycle Health Projection</Text>
          <Text style={styles.sectionDescription}>Simulated plant-health index across four growth milestones. The curve is a scenario projection, not observed field telemetry.</Text>
          {simulationResult && simulationResult.daily_health_history.length > 0 ? (
            <LineChart
              data={{
                labels: simulationResult.daily_health_history.map((point) => point.milestone),
                datasets: [
                  {
                    data: simulationResult.daily_health_history.map((point) => Math.max(0, Math.min(100, point.health_percentage))),
                    color: (opacity = 1) => `rgba(${chartRgb}, ${opacity})`,
                    strokeWidth: 3,
                  },
                  {
                    data: simulationResult.daily_health_history.map(() => 100),
                    color: () => "rgba(0,0,0,0)",
                    strokeWidth: 0,
                    withDots: false,
                  },
                ],
                legend: [],
              }}
              width={chartWidth}
              height={230}
              fromZero
              segments={4}
              yAxisSuffix="%"
              yAxisInterval={1}
              withInnerLines
              withOuterLines={false}
              withDots
              withShadow={false}
              bezier
              chartConfig={{
                backgroundColor: "#FFFFFF",
                backgroundGradientFrom: "#FFFFFF",
                backgroundGradientTo: "#FFFFFF",
                decimalPlaces: 0,
                color: (opacity = 1) => `rgba(55, 75, 62, ${opacity})`,
                labelColor: (opacity = 1) => `rgba(93, 109, 98, ${opacity})`,
                propsForBackgroundLines: { stroke: "#E7EEE8", strokeDasharray: "4 5" },
                propsForDots: { r: "4", strokeWidth: "2", stroke: chartColor },
              }}
              style={styles.chart}
              accessibilityLabel="Simulated plant health from sowing to maturity"
            />
          ) : (
            <View style={styles.chartPlaceholder}><Text style={styles.chartPlaceholderText}>The lifecycle chart will appear when simulation data is available.</Text></View>
          )}
          {simulationResult && <Text style={[styles.chartSummary, { color: chartColor }]}>Final health index: {finalHealthIndex?.toFixed(1)}% · {finalHealthIndex !== null && finalHealthIndex > 80 ? "Healthy" : finalHealthIndex !== null && finalHealthIndex >= 50 ? "Watch" : "Stressed"}</Text>}
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Sync Local Field Weather</Text>
          <Text style={styles.sectionDescription}>Fetch the previous seven days of local maximum temperature and rainfall from Open-Meteo, then use them as the simulation climate baseline.</Text>
          <View style={styles.coordinateRow}>
            <View style={styles.coordinateField}>
              <Text style={styles.inputLabel}>Latitude</Text>
              <TextInput value={latitudeInput} onChangeText={setLatitudeInput} keyboardType="numbers-and-punctuation" placeholder="17.3850" placeholderTextColor="#9AA69D" style={styles.coordinateInput} accessibilityLabel="Field latitude" />
            </View>
            <View style={styles.coordinateField}>
              <Text style={styles.inputLabel}>Longitude</Text>
              <TextInput value={longitudeInput} onChangeText={setLongitudeInput} keyboardType="numbers-and-punctuation" placeholder="78.4867" placeholderTextColor="#9AA69D" style={styles.coordinateInput} accessibilityLabel="Field longitude" />
            </View>
          </View>
          <Pressable accessibilityRole="button" disabled={weatherSyncLoading || simulationLoading} onPress={syncLocalFieldWeather} style={[styles.syncButton, (weatherSyncLoading || simulationLoading) && styles.syncButtonDisabled]}>
            {weatherSyncLoading ? <ActivityIndicator color="#FFFFFF" size="small" /> : <Text style={styles.syncButtonText}>Sync Local Field Weather</Text>}
          </Pressable>
          {simulationResult?.weather_summary && <Text style={styles.weatherSummary}>Last sync: {simulationResult.weather_summary.average_max_temperature_c.toFixed(1)}°C average max · {simulationResult.weather_summary.total_precipitation_mm.toFixed(1)} mm total rain ({simulationResult.weather_summary.days_included} daily records)</Text>}
        </View>

        <View style={styles.section}>
          <Text style={styles.sectionTitle}>GENETIC PROFILE</Text>
          <Text style={styles.sectionDescription}>Crop varieties are loaded live from the database-backed API catalog.</Text>
          {isLoading && <View style={styles.loadingRow}><ActivityIndicator color="#287A55" size="small" /><Text style={styles.loadingText}>Loading crop catalog...</Text></View>}
          {!isLoading && cropCatalog.map((crop) => {
            const selected = selectedCrop === crop.crop_name;
            return (
              <Pressable key={crop.id} accessibilityRole="radio" accessibilityState={{ selected }} onPress={() => setSelectedCrop(crop.crop_name)} style={[styles.varietyButton, selected && styles.varietyButtonSelected]}>
                <View style={[styles.radioOuter, selected && styles.radioOuterSelected]}>{selected && <View style={styles.radioInner} />}</View>
                <View style={styles.varietyTextContainer}>
                  <Text style={[styles.varietyName, selected && styles.varietyNameSelected]}>{crop.crop_name}</Text>
                  <Text style={styles.varietyDescription}>Hybrid code: {crop.hybrid_code} · Base yield: {crop.base_yield_kg_per_acre.toLocaleString("en-IN")} kg/acre</Text>
                </View>
              </Pressable>
            );
          })}
          {!isLoading && !catalogError && cropCatalog.length === 0 && <Text style={styles.errorText}>No crop varieties are available in the database.</Text>}
        </View>

        {activeCrop && (
          <View style={styles.card}>
            <Text style={styles.cardTitle}>Base Genetic Resilience</Text>
            <Text style={styles.sectionDescription}>Reference coefficients for {activeCrop.hybrid_code}; values are shown as percentages.</Text>
            <View style={styles.resilienceGrid}>
              <View style={styles.resilienceItem}><Text style={styles.smallLabel}>Heat resilience</Text><Text style={styles.resilienceValue}>{resiliencePercent(activeCrop.heat_resilience_factor)}</Text></View>
              <View style={styles.resilienceItem}><Text style={styles.smallLabel}>Drought resilience</Text><Text style={styles.resilienceValue}>{resiliencePercent(activeCrop.drought_resilience_factor)}</Text></View>
              <View style={styles.resilienceItem}><Text style={styles.smallLabel}>Disease resistance</Text><Text style={styles.resilienceValue}>{resiliencePercent(activeCrop.disease_resistance_factor)}</Text></View>
              <View style={styles.resilienceItem}><Text style={styles.smallLabel}>Pest resistance</Text><Text style={styles.resilienceValue}>{resiliencePercent(activeCrop.pest_resistance_factor)}</Text></View>
            </View>
          </View>
        )}

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Environmental Factors</Text>
          <Text style={styles.sectionDescription}>Adjust temperature and irrigation deviations.</Text>
          <SliderControl title="Temperature Shift" value={tempShift} minimumValue={-5} maximumValue={5} step={0.5} unit=" °C" onValueChange={setTempShift} />
          <SliderControl title="Irrigation Variance" value={waterAdjust} minimumValue={-50} maximumValue={50} step={1} unit="%" onValueChange={setWaterAdjust} />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Biological Pressures</Text>
          <Text style={styles.sectionDescription}>Model pest pressure and disease spread.</Text>
          <SliderControl title="Pest Pressure" value={pestPressure} minimumValue={0} maximumValue={100} step={1} unit="%" onValueChange={setPestPressure} />
          <SliderControl title="Disease Spread" value={diseasePressure} minimumValue={0} maximumValue={100} step={1} unit="%" onValueChange={setDiseasePressure} />
        </View>

        <View style={styles.card}>
          <Text style={styles.cardTitle}>Seed Quality</Text>
          <Text style={styles.sectionDescription}>Enter the batch germination laboratory result.</Text>
          <SliderControl title="Batch Seed Germination Lab Rate" value={germinationRate} minimumValue={50} maximumValue={100} step={1} unit="%" onValueChange={setGerminationRate} />
        </View>

        <Pressable accessibilityRole="button" onPress={resetSimulation} style={styles.resetButton}>
          <Text style={styles.resetButtonText}>Reset Sandbox</Text>
        </Pressable>
        <Text style={styles.footer}>Scenario simulation only · Not a field-yield guarantee</Text>
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: "#F4F7F3" },
  container: { paddingHorizontal: 20, paddingTop: 18, paddingBottom: 36 },
  header: { marginBottom: 22 },
  eyebrow: { color: "#287A55", fontSize: 11, fontWeight: "800", letterSpacing: 1.8, marginBottom: 8 },
  title: { color: "#173B2C", fontSize: 32, fontWeight: "800" },
  subtitle: { color: "#66756C", fontSize: 14, marginTop: 5 },
  metricsCard: { backgroundColor: "#FFFFFF", borderRadius: 20, borderWidth: 1, borderColor: "#E0E9E1", padding: 20, marginBottom: 26 },
  metricLabel: { color: "#697A6F", fontSize: 11, fontWeight: "800", letterSpacing: 1.2 },
  yieldRow: { flexDirection: "row", alignItems: "baseline", marginTop: 12, marginBottom: 18, flexWrap: "wrap" },
  yieldValue: { color: "#173B2C", fontSize: 38, fontWeight: "800", fontVariant: ["tabular-nums"] },
  yieldUnit: { color: "#66756C", fontSize: 14, marginLeft: 8 },
  metricsFooter: { borderTopWidth: 1, borderTopColor: "#E9EEE9", paddingTop: 15, flexDirection: "row", justifyContent: "space-between" },
  smallLabel: { color: "#748177", fontSize: 12 },
  riskValue: { fontSize: 17, fontWeight: "800", marginTop: 5 },
  lossBlock: { alignItems: "flex-end" },
  lossValue: { color: "#25392D", fontSize: 17, fontWeight: "800", marginTop: 5 },
  loadingRow: { flexDirection: "row", alignItems: "center", marginTop: 16, gap: 9 },
  loadingText: { color: "#65756A", fontSize: 12 },
  errorBox: { backgroundColor: "#FFF1F0", borderRadius: 10, padding: 12, marginTop: 15 },
  errorText: { color: "#A52D2D", fontSize: 12, lineHeight: 18 },
  retryButton: { alignSelf: "flex-start", paddingTop: 9 },
  retryText: { color: "#8F2727", fontWeight: "700", fontSize: 12 },
  section: { marginBottom: 26 },
  sectionTitle: { color: "#244C36", fontSize: 12, fontWeight: "800", letterSpacing: 1.1 },
  sectionDescription: { color: "#748177", fontSize: 13, lineHeight: 19, marginTop: 8, marginBottom: 16 },
  varietyButton: { flexDirection: "row", alignItems: "center", backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E0E8E1", borderRadius: 13, padding: 14, marginBottom: 10 },
  varietyButtonSelected: { borderColor: "#287A55", backgroundColor: "#EDF6EF" },
  radioOuter: { width: 20, height: 20, borderRadius: 10, borderWidth: 1.5, borderColor: "#A7B5AA", alignItems: "center", justifyContent: "center", marginRight: 12 },
  radioOuterSelected: { borderColor: "#287A55" },
  radioInner: { width: 10, height: 10, borderRadius: 5, backgroundColor: "#287A55" },
  varietyTextContainer: { flex: 1 },
  varietyName: { color: "#435348", fontSize: 13, fontWeight: "700" },
  varietyNameSelected: { color: "#1F603F" },
  varietyDescription: { color: "#7B887F", fontSize: 11, marginTop: 5 },
  card: { backgroundColor: "#FFFFFF", borderWidth: 1, borderColor: "#E0E9E1", borderRadius: 18, padding: 16, marginBottom: 18 },
  chart: { borderRadius: 14, marginLeft: -8 },
  chartPlaceholder: { minHeight: 150, borderRadius: 12, backgroundColor: "#F8FAF8", alignItems: "center", justifyContent: "center", padding: 20 },
  chartPlaceholderText: { color: "#748177", fontSize: 12, textAlign: "center", lineHeight: 18 },
  chartSummary: { fontSize: 13, fontWeight: "800", marginTop: 8 },
  coordinateRow: { flexDirection: "row", gap: 12 },
  coordinateField: { flex: 1 },
  inputLabel: { color: "#435348", fontSize: 12, fontWeight: "700", marginBottom: 7 },
  coordinateInput: { backgroundColor: "#F8FAF8", borderWidth: 1, borderColor: "#DCE6DD", borderRadius: 10, paddingHorizontal: 12, paddingVertical: 11, color: "#25392D", fontSize: 14 },
  syncButton: { backgroundColor: "#287A55", borderRadius: 11, paddingVertical: 13, paddingHorizontal: 12, alignItems: "center", justifyContent: "center", marginTop: 14, minHeight: 44 },
  syncButtonDisabled: { opacity: 0.65 },
  syncButtonText: { color: "#FFFFFF", fontSize: 13, fontWeight: "800" },
  weatherSummary: { color: "#52675A", fontSize: 12, lineHeight: 18, marginTop: 12 },
  resilienceGrid: { flexDirection: "row", flexWrap: "wrap", gap: 12 },
  resilienceItem: { width: "47%", backgroundColor: "#F8FAF8", borderRadius: 12, padding: 12 },
  resilienceValue: { color: "#287A55", fontSize: 18, fontWeight: "800", marginTop: 6 },
  control: { backgroundColor: "#F8FAF8", borderWidth: 1, borderColor: "#E7EEE8", borderRadius: 14, padding: 15, marginBottom: 12 },
  controlHeader: { flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 10 },
  controlTitle: { color: "#344B3A", fontSize: 13, fontWeight: "700", flex: 1 },
  controlValue: { color: "#287A55", fontSize: 14, fontWeight: "800", fontVariant: ["tabular-nums"] },
  slider: { width: "100%", height: 38, marginTop: 9 },
  rangeLabels: { flexDirection: "row", justifyContent: "space-between" },
  rangeText: { color: "#879289", fontSize: 11 },
  resetButton: { backgroundColor: "#E5EEE6", borderRadius: 12, paddingVertical: 15, alignItems: "center" },
  resetButtonText: { color: "#24553A", fontSize: 14, fontWeight: "800" },
  footer: { color: "#8A958C", fontSize: 11, textAlign: "center", marginTop: 22, lineHeight: 17 }
});
