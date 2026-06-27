import { useRef, useState } from "react";
import {
  ActivityIndicator,
  Alert,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";
import { CameraView, useCameraPermissions } from "expo-camera";
import * as ImagePicker from "expo-image-picker";
import { router } from "expo-router";

import { backendConfigIssues, hasValidBackendConfig } from "../src/config";
import { submitInvoice } from "../src/services/faturexApi";
import {
  buildQrDataJson,
  parseAtQrString,
  type AtQrPayload,
  type DocumentType,
  QrValidationError,
} from "../src/utils/qrValidation";

type FlowMode = "scan" | "capture";
type SubmitState = "idle" | "scanning" | "qr_ready" | "capturing" | "sending" | "success" | "error";

export default function HomeScreen() {
  const cameraRef = useRef<CameraView | null>(null);
  const [cameraPermission, requestCameraPermission] = useCameraPermissions();
  const [mediaPermission, requestMediaPermission] = ImagePicker.useMediaLibraryPermissions();

  const [mode, setMode] = useState<FlowMode>("scan");
  const [submitState, setSubmitState] = useState<SubmitState>("idle");
  const [message, setMessage] = useState("Aguardando leitura do QR Code...");
  const [qrPayload, setQrPayload] = useState<AtQrPayload | null>(null);
  const [selectedType, setSelectedType] = useState<DocumentType | null>(null);
  const [observacoes, setObservacoes] = useState("");
  const [imageUri, setImageUri] = useState<string | null>(null);
  const [imageName, setImageName] = useState<string | undefined>(undefined);
  const [imageType, setImageType] = useState<string | undefined>(undefined);
  const [isSending, setIsSending] = useState(false);

  const cameraReady = cameraPermission?.granted ?? false;
  const mediaReady = mediaPermission?.granted ?? false;

  const resetFlow = () => {
    setMode("scan");
    setSubmitState("idle");
    setMessage("Aguardando leitura do QR Code...");
    setQrPayload(null);
    setSelectedType(null);
    setObservacoes("");
    setImageUri(null);
    setImageName(undefined);
    setImageType(undefined);
    setIsSending(false);
  };

  const handleBarcodeScanned = ({ data }: { data: string }) => {
    if (mode !== "scan") {
      return;
    }

    try {
      const parsed = parseAtQrString(data);
      setQrPayload(parsed);
      setMessage("QR Code lido com sucesso.");
      setSubmitState("qr_ready");
      setMode("capture");
      Alert.alert("QR Code lido com sucesso");
    } catch (error) {
      const errorMessage = error instanceof QrValidationError ? error.message : "QR Code inválido.";
      setSubmitState("error");
      setMessage(errorMessage);
      Alert.alert("QR inválido", errorMessage);
    }
  };

  const takePhoto = async () => {
    if (!cameraReady) {
      const permission = await requestCameraPermission();
      if (!permission.granted) {
        setMessage("Permissão de câmara recusada.");
        return;
      }
    }

    try {
      const photo = await cameraRef.current?.takePictureAsync({ quality: 0.8 });

      if (!photo?.uri) {
        setMessage("Não foi possível capturar a foto.");
        return;
      }

      setImageUri(photo.uri);
      setImageName("fatura-capturada.jpg");
      setImageType("image/jpeg");
      setSubmitState("capturing");
      setMessage("Foto capturada.");
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Falha ao tirar a foto.";
      setSubmitState("error");
      setMessage(errorMessage);
      Alert.alert("Erro na câmara", errorMessage);
    }
  };

  const chooseFromGallery = async () => {
    if (!mediaReady) {
      const permission = await requestMediaPermission();
      if (!permission.granted) {
        setMessage("Permissão da galeria recusada.");
        return;
      }
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      allowsEditing: false,
    });

    if (result.canceled || !result.assets.length) {
      return;
    }

    const asset = result.assets[0];
    setImageUri(asset.uri);
    setImageName(asset.fileName ?? "fatura-galeria.jpg");
    setImageType(asset.mimeType ?? "image/jpeg");
    setSubmitState("capturing");
    setMessage("Imagem carregada da galeria.");
  };

  const handleSubmit = async () => {
    if (!qrPayload) {
      setMessage("Ler o QR Code antes de enviar.");
      return;
    }

    if (!selectedType) {
      setMessage("Selecionar Despesa ou Receita.");
      return;
    }

    if (!imageUri) {
      setMessage("Capturar ou escolher uma foto antes de enviar.");
      return;
    }

    if (!hasValidBackendConfig) {
      setMessage("Configuração do backend em falta no ficheiro .env.");
      return;
    }

    setIsSending(true);
    setSubmitState("sending");
    setMessage("A enviar...");

    try {
      const result = await submitInvoice({
        qrPayload,
        tipo: selectedType,
        observacoes,
        imageUri,
        imageName,
        imageType,
      });

      setSubmitState("success");
      setMessage(`Fatura registada com sucesso! Categoria: ${result.categoria}`);
      Alert.alert("Fatura registada com sucesso!", `Categoria: ${result.categoria}`);
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : "Erro inesperado no envio.";
      setSubmitState("error");
      setMessage(errorMessage);
      Alert.alert("Erro ao enviar", errorMessage);
    } finally {
      setIsSending(false);
    }
  };

  const qrPreview = qrPayload ? buildQrDataJson(qrPayload.raw_qr_string) : "";

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>FatureX</Text>
      <Text style={styles.subtitle}>Fluxo core mobile</Text>

      {backendConfigIssues.length > 0 ? (
        <View style={styles.warningBox}>
          <Text style={styles.warningText}>Configuração do backend em falta</Text>
          {backendConfigIssues.map((issue) => (
            <Text key={issue} style={styles.warningDetail}>
              {issue}
            </Text>
          ))}
        </View>
      ) : null}

      <View style={styles.statusBox}>
        <Text style={styles.statusLabel}>Estado</Text>
        <Text style={styles.statusText}>{message}</Text>
      </View>

      <View style={styles.cameraFrame}>
        {mode === "scan" ? (
          cameraReady ? (
            <CameraView
              ref={cameraRef}
              style={styles.camera}
              facing="back"
              barcodeScannerSettings={{ barcodeTypes: ["qr"] }}
              onBarcodeScanned={handleBarcodeScanned}
            />
          ) : (
            <View style={styles.permissionBox}>
              <Text style={styles.permissionText}>A câmara precisa de permissão.</Text>
              <Pressable style={styles.button} onPress={requestCameraPermission}>
                <Text style={styles.buttonText}>Autorizar câmara</Text>
              </Pressable>
            </View>
          )
        ) : imageUri ? (
          <Image source={{ uri: imageUri }} style={styles.previewImage} />
        ) : cameraReady ? (
          <CameraView ref={cameraRef} style={styles.camera} facing="back" />
        ) : (
          <View style={styles.permissionBox}>
            <Text style={styles.permissionText}>A câmara precisa de permissão.</Text>
            <Pressable style={styles.button} onPress={requestCameraPermission}>
              <Text style={styles.buttonText}>Autorizar câmara</Text>
            </Pressable>
          </View>
        )}
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Tipo de documento</Text>
        <View style={styles.row}>
          {(["Despesa", "Receita"] as DocumentType[]).map((type) => {
            const active = selectedType === type;
            return (
              <Pressable
                key={type}
                onPress={() => setSelectedType(type)}
                style={[styles.toggleButton, active && styles.toggleButtonActive]}
              >
                <Text style={[styles.toggleText, active && styles.toggleTextActive]}>{type}</Text>
              </Pressable>
            );
          })}
        </View>
          <TextInput
            value={observacoes}
            onChangeText={setObservacoes}
            placeholder="Observações (opcional)"
            placeholderTextColor="#9ca3af"
            multiline
            numberOfLines={3}
            style={styles.textInput}
          />
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Ações</Text>
        <View style={styles.row}>
          <Pressable style={styles.button} onPress={takePhoto}>
            <Text style={styles.buttonText}>Tirar foto</Text>
          </Pressable>
          <Pressable style={styles.button} onPress={chooseFromGallery}>
            <Text style={styles.buttonText}>Galeria</Text>
          </Pressable>
        </View>
        <View style={styles.row}>
          <Pressable style={styles.secondaryButton} onPress={resetFlow}>
            <Text style={styles.secondaryButtonText}>Reiniciar</Text>
          </Pressable>
          <Pressable
            style={[styles.button, (!qrPayload || !selectedType || !imageUri || isSending) && styles.buttonDisabled]}
            onPress={handleSubmit}
            disabled={!qrPayload || !selectedType || !imageUri || isSending}
          >
            {isSending ? (
              <ActivityIndicator color="#fff" />
            ) : (
              <Text style={styles.buttonText}>Enviar</Text>
            )}
          </Pressable>
        </View>
        <Pressable style={styles.secondaryButton} onPress={() => router.push("/relatorios" as never) }>
          <Text style={styles.secondaryButtonText}>Abrir Exportação</Text>
        </Pressable>
      </View>

      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Resumo do QR</Text>
        <Text style={styles.monoText}>ATCUD: {qrPayload?.atcud ?? "-"}</Text>
        <Text style={styles.monoText}>NIF: {qrPayload?.nif_emissor ?? "-"}</Text>
        <Text style={styles.monoText}>Data: {qrPayload?.data_fatura ?? "-"}</Text>
        <Text style={styles.monoText}>Total: {qrPayload?.valor_total ?? "-"}</Text>
        <Text style={styles.monoText}>IVA: {qrPayload?.imposto_total ?? "-"}</Text>
        <Text style={styles.monoText} numberOfLines={4}>
          Raw: {qrPayload?.raw_qr_string ?? "-"}
        </Text>
        <Text style={styles.debugText} numberOfLines={4}>
          JSON: {qrPreview || "-"}
        </Text>
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
  warningBox: {
    borderWidth: 1,
    borderColor: "#d97706",
    backgroundColor: "#fff7ed",
    padding: 12,
    gap: 4,
  },
  warningText: {
    color: "#9a3412",
    fontWeight: "700",
  },
  warningDetail: {
    color: "#9a3412",
  },
  statusBox: {
    borderWidth: 1,
    borderColor: "#d1d5db",
    backgroundColor: "#fff",
    padding: 12,
    gap: 6,
  },
  statusLabel: {
    fontSize: 12,
    textTransform: "uppercase",
    color: "#6b7280",
    fontWeight: "700",
  },
  statusText: {
    color: "#111",
    fontSize: 15,
    lineHeight: 21,
  },
  cameraFrame: {
    height: 320,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    backgroundColor: "#111827",
    overflow: "hidden",
  },
  camera: {
    flex: 1,
  },
  previewImage: {
    width: "100%",
    height: "100%",
    resizeMode: "cover",
  },
  permissionBox: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 16,
    gap: 12,
    backgroundColor: "#111827",
  },
  permissionText: {
    color: "#fff",
    textAlign: "center",
    fontSize: 16,
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
    flexGrow: 1,
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
    flexGrow: 1,
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
  monoText: {
    color: "#111",
    fontFamily: "monospace",
    fontSize: 13,
  },
  debugText: {
    color: "#6b7280",
    fontFamily: "monospace",
    fontSize: 12,
  },
  textInput: {
    minHeight: 72,
    borderWidth: 1,
    borderColor: "#cbd5e1",
    paddingHorizontal: 12,
    paddingVertical: 10,
    color: "#111",
    textAlignVertical: "top",
    backgroundColor: "#fff",
  },
});
