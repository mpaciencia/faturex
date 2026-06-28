import { useMemo, useState } from "react";
import { ActivityIndicator, Alert, Pressable, ScrollView, StyleSheet, Text, View } from "react-native";
import * as FileSystem from "expo-file-system";
import * as Sharing from "expo-sharing";

import { FATUREX_API_BASE_URL, FATUREX_API_KEY, hasValidBackendConfig } from "../src/config";

type Quarter = 1 | 2 | 3 | 4;

const quarterLabels: Record<Quarter, string> = {
  1: "T1",
  2: "T2",
  3: "T3",
  4: "T4",
};

function getCurrentQuarter(date = new Date()): Quarter {
  return Math.floor(date.getMonth() / 3) + 1 as Quarter;
}

function getQuarterRange(year: number, quarter: Quarter) {
  const startMonth = (quarter - 1) * 3;
  const endMonth = startMonth + 2;
  const dataInicio = new Date(year, startMonth, 1);
  const dataFim = new Date(year, endMonth + 1, 0);

  return {
    dataInicio: dataInicio.toISOString().slice(0, 10),
    dataFim: dataFim.toISOString().slice(0, 10),
  };
}

async function downloadAndShareReport(url: string, fileName: string, mimeType: string) {
  if (!hasValidBackendConfig) {
    throw new Error("Configuração do backend em falta no ficheiro .env.");
  }

  const targetDirectory = new FileSystem.Directory(FileSystem.Paths.cache);
  const targetFile = new FileSystem.File(targetDirectory, fileName);

  const result = await FileSystem.File.downloadFileAsync(url, targetFile, {
    headers: {
      "X-API-Key": FATUREX_API_KEY,
    },
    idempotent: true,
  });

  const available = await Sharing.isAvailableAsync();
  if (!available) {
    throw new Error("Partilha indisponível neste dispositivo.");
  }

  await Sharing.shareAsync(result.uri, {
    mimeType,
    dialogTitle: fileName,
  });
}

export default function RelatoriosScreen() {
  const year = new Date().getFullYear();
  const [quarter, setQuarter] = useState<Quarter>(getCurrentQuarter());
  const [isDownloading, setIsDownloading] = useState<"excel" | "zip" | null>(null);

  const range = useMemo(() => getQuarterRange(year, quarter), [quarter, year]);

  const buildUrl = (endpoint: string) => {
    if (!FATUREX_API_BASE_URL) {
      throw new Error("Definir EXPO_PUBLIC_FATUREX_API_BASE_URL.");
    }

    const query = new URLSearchParams({
      data_inicio: range.dataInicio,
      data_fim: range.dataFim,
    });

    return `${FATUREX_API_BASE_URL}${endpoint}?${query.toString()}`;
  };

  const handleDownload = async (kind: "excel" | "zip") => {
    setIsDownloading(kind);

    try {
      const config = kind === "excel"
        ? {
            url: buildUrl("/api/relatorios/excel"),
            fileName: `relatorio_${range.dataInicio}_${range.dataFim}.xlsx`,
            mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
          }
        : {
            url: buildUrl("/api/relatorios/zip"),
            fileName: `faturas_${range.dataInicio}_${range.dataFim}.zip`,
            mimeType: "application/zip",
          };

      await downloadAndShareReport(config.url, config.fileName, config.mimeType);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Erro inesperado no download.";
      Alert.alert("Erro", message);
    } finally {
      setIsDownloading(null);
    }
  };

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Exportação</Text>
      <Text style={styles.subtitle}>Ano {year} • {range.dataInicio} → {range.dataFim}</Text>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Trimestre</Text>
        <View style={styles.row}>
          {( [1, 2, 3, 4] as Quarter[] ).map((item) => {
            const active = quarter === item;
            return (
              <Pressable
                key={item}
                style={[styles.toggleButton, active && styles.toggleButtonActive]}
                onPress={() => setQuarter(item)}
              >
                <Text style={[styles.toggleText, active && styles.toggleTextActive]}>{quarterLabels[item]}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Downloads</Text>
        <Pressable
          style={[styles.button, isDownloading === "excel" && styles.buttonDisabled]}
          onPress={() => handleDownload("excel")}
          disabled={isDownloading !== null}
        >
          {isDownloading === "excel" ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Descarregar Relatório Excel</Text>}
        </Pressable>

        <Pressable
          style={[styles.secondaryButton, isDownloading === "zip" && styles.buttonDisabled]}
          onPress={() => handleDownload("zip")}
          disabled={isDownloading !== null}
        >
          {isDownloading === "zip" ? <ActivityIndicator color="#111827" /> : <Text style={styles.secondaryButtonText}>Descarregar ZIP com Faturas</Text>}
        </Pressable>
      </View>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: {
    flexGrow: 1,
    padding: 20,
    paddingTop: 64,
    backgroundColor: "#f4f4f4",
    gap: 16,
  },
  title: {
    fontSize: 32,
    fontWeight: "700",
    color: "#111",
  },
  subtitle: {
    fontSize: 16,
    color: "#555",
    marginBottom: 8,
  },
  section: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
    padding: 12,
    gap: 12,
  },
  sectionTitle: {
    fontSize: 14,
    fontWeight: "700",
    color: "#111",
    textTransform: "uppercase",
  },
  row: {
    flexDirection: "row",
    gap: 10,
    flexWrap: "wrap",
  },
  button: {
    minHeight: 44,
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: "#111827",
    justifyContent: "center",
    alignItems: "center",
  },
  buttonDisabled: {
    opacity: 0.5,
  },
  buttonText: {
    color: "#fff",
    fontWeight: "700",
  },
  secondaryButton: {
    minHeight: 44,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "#111827",
    justifyContent: "center",
    alignItems: "center",
  },
  secondaryButtonText: {
    color: "#111827",
    fontWeight: "700",
  },
  toggleButton: {
    minHeight: 44,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderWidth: 1,
    borderColor: "#111827",
    justifyContent: "center",
    alignItems: "center",
    flexGrow: 1,
  },
  toggleButtonActive: {
    backgroundColor: "#111827",
  },
  toggleText: {
    color: "#111827",
    fontWeight: "700",
  },
  toggleTextActive: {
    color: "#fff",
  },
});